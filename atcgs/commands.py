"""The @cgs identity verbs: init, request, admit, revoke, login (README § 3).

Logins and passwords are asked with getpass: never read from argv, the
environment or a file, and never printed. Outputs carry UIDs, public keys,
fingerprints and paths only.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Callable, Mapping

from ComplexGitSync.orchestre.op_levels import LEVELS, LevelCommand

from atcgs import PRIVATE, REGISTER_ENV, ROOT, Authorization, Request, Unauthorized
from atcgs.glyph import SshKey, reseal
from atcgs.identity import Identity, derive
from atcgs.journal import (
    ROLES,
    Journal,
    JournalError,
    Register,
    canonical,
    enrol_statement,
    fingerprint,
)
from atcgs.session import AccessRefused, Session, repo_path

OPX_PUB_ENV = "ATCGS_OPX_PUB"  # overrides the pin, for the lab and the tests
GLYPHS_ENV = "ATCGS_GLYPHS"  # where a user's GLYPHs live; default ~/.cgs/.glyph
# A level's 4-bit code is its PoE vector over (NAME, NODE, EDGE, OP), from ComplexGitSync:
# OPX 0000, DEV 1000, USR 1100, PUB 1111. OPX is POE.
ROLE_CODES: Mapping[str, str] = {
    level: "".join("1" if bit else "0" for bit in (poe.name, poe.node, poe.edge, poe.op))
    for level, poe in LEVELS.items()
}

ask: Callable[[str], str] = getpass.getpass  # replaced in tests only


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def opx_pub(env: Mapping[str, str] | None = None) -> bytes:
    """OPX's IDPUB: ATCGS_OPX_PUB, else spec/contracts.toml [identity] opx_pub."""
    text = _env(env).get(OPX_PUB_ENV)
    if text is None:
        with (ROOT / "spec/contracts.toml").open("rb") as handle:
            text = tomllib.load(handle).get("identity", {}).get("opx_pub", "")
    if not text:
        raise ValueError("no OPX key is pinned: run `@cgs OPX init` and copy its idpub into "
                         "spec/contracts.toml [identity] opx_pub")
    pub = base64.b64decode(text, validate=True)
    if len(pub) != 32:
        raise ValueError("the pinned OPX key is not a 32-byte Ed25519 key")
    return pub


# atCGS's register: per-project, private, in the project's own memory (.cgitsync/.memory).
# cgitsync's memory scanner matches only its own folder names, so this folder is ignored by it.
REGISTER = ROOT / PRIVATE / ".memory" / ".register"
IDENTITIES_ENV = "ATCGS_IDENTITIES"  # overrides the published identities file (tests, other layouts)
# The identities OPX publishes to .omniscience (MolonariCgsMolo S1): UIDs and public keys, no names.
PUBLISHED = Path(".omniscience") / "atcgs" / "identity.jsonl"
PUBLISH_BRANCH = "CGS-MOLO"  # until the development is validated; then main (ticket D2)


def project_root(env: Mapping[str, str] | None = None) -> Path:
    """The project this atCGS serves: the nearest directory at or above atCGS holding `.cgitsync/`.

    Where atCGS is the project's own root that is atCGS itself; where it is a read-only mount
    inside another project's tree, it is that project's root, and the register is that project's.
    """
    for directory in (ROOT, *ROOT.parents):
        if (directory / PRIVATE).is_dir():
            return directory
    return ROOT


def is_master(env: Mapping[str, str] | None = None) -> bool:
    """Whether this register is the master copy, the only one that enrols identities."""
    return bool(_env(env).get(REGISTER_ENV)) or project_root(env) == ROOT


def register(env: Mapping[str, str] | None = None) -> Register:
    """The project's register: <project>/.cgitsync/.memory/.register, unless ATCGS_REGISTER names another."""
    directory = _env(env).get(REGISTER_ENV)
    base = project_root(env)
    if not directory and not (base / PRIVATE / ".memory").is_dir():
        raise ValueError(f"no {PRIVATE}/.memory mount here for the register: mount it (OPX tree) or set {REGISTER_ENV}")
    return Register(Path(directory) if directory else base / PRIVATE / ".memory" / ".register", opx_pub(env))


def published_identities(env: Mapping[str, str] | None = None) -> Path:
    override = _env(env).get(IDENTITIES_ENV)
    return Path(override) if override else project_root(env) / PUBLISHED


def sync_identities(reg: Register, env: Mapping[str, str] | None = None) -> int:
    """Bring a project register's identity journal level with the published one; return lines added.

    The published copy is verified against the pinned OPX key first. A register that already holds
    a line the published copy does not (or a different one) has gone its own way: refused, never merged.
    """
    if is_master(env):
        return 0
    source = Journal(published_identities(env), "identity").entries()
    if not source:
        return 0
    reg.state()  # the local register verifies as it stands
    reg.verify_identities(source)
    local = reg.identity.entries()
    if source[:len(local)] != local:
        raise JournalError("this project's identity journal differs from the published one: refused, not merged")
    if len(source) > len(local):
        reg.identity.write(source)
    return len(source) - len(local)


def glyph_path(uid: str, env: Mapping[str, str] | None = None) -> Path:
    base = _env(env).get(GLYPHS_ENV)
    return (Path(base) if base else Path.home() / ".cgs" / ".glyph") / f"{uid}.glyph"


def ask_identity(who: str, confirm: bool = False) -> Identity:
    login = ask(f"{who} login: ")
    password = ask(f"{who} password: ")
    if confirm and ask(f"{who} password again: ") != password:
        raise ValueError("the two passwords differ")
    return derive(login, password)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    draft = path.with_name(f".{path.name}.tmp")
    draft.touch(mode=0o600)
    draft.write_bytes(data)
    os.replace(draft, path)


def _opx(reg: Register) -> Identity:
    opx = ask_identity("OPX")
    if opx.pub != reg.opx_pub:
        raise Unauthorized("this login/password is not OPX's pinned key")
    return opx


def _master_only(what: str, env: Mapping[str, str] | None) -> None:
    """Identities are enrolled in the master register only; a project register copies them."""
    if not is_master(env):
        raise Unauthorized(f"{what} is done in the master register (the cgs workspace), then "
                           "`@cgs OPX publish`; this project's register only copies identities")


def init(authorization: Authorization, env: Mapping[str, str] | None = None) -> dict[str, object]:
    authorization.require("OPX")
    _master_only("OPX init", env)
    opx = ask_identity("OPX", confirm=True)
    try:
        pinned = opx_pub(env)
    except ValueError:
        return {"layer": "OPX", "uid": opx.uid, "idpub": _b64(opx.pub), "pinned": False,
                "next": "copy idpub into spec/contracts.toml [identity] opx_pub, then run OPX init again"}
    if pinned != opx.pub:
        raise Unauthorized("this login/password does not match the pinned OPX key")
    register(env).init(opx)
    return {"layer": "OPX", "uid": opx.uid, "pinned": True, "enrolled": True}


def request(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    out, pairs = Path(args[0]), list(zip(args[1::2], args[2::2]))
    for _, role in pairs:
        if role not in ROLES:
            raise ValueError(f"a role is one of {', '.join(ROLES)}, not {role!r}")
    me = ask_identity(layer, confirm=True)
    keys = [SshKey.generate(repo, role) for repo, role in pairs]
    path = glyph_path(me.uid, env)
    _write_private(path, reseal(me, path.read_bytes() if path.exists() else None, keys))
    listed = [{"repo": k.repo, "role": k.role, "ssh": k.public} for k in keys]
    doc = {"uid": me.uid, "pub": _b64(me.pub), "proof": _b64(me.sign(enrol_statement(me.pub))), "keys": listed}
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {"uid": me.uid, "glyph": str(path), "request": str(out),
            "keys": [{"repo": k["repo"], "role": k["role"], "fingerprint": fingerprint(k["ssh"])} for k in listed]}


def admit(authorization: Authorization, args: tuple[str, ...],
          env: Mapping[str, str] | None = None) -> dict[str, object]:
    authorization.require("OPX")
    doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    reg = register(env)
    opx = _opx(reg)
    sync_identities(reg, env)
    if not reg.state().known(doc["uid"]):
        _master_only("enrolling a new identity", env)
        reg.enrol(opx, base64.b64decode(doc["pub"], validate=True), base64.b64decode(doc["proof"], validate=True))
    granted = []
    for key in doc["keys"]:
        reg.grant(opx, doc["uid"], key["repo"], key["role"], key["ssh"])
        granted.append({"repo": key["repo"], "role": key["role"], "fingerprint": fingerprint(key["ssh"])})
    return {"uid": doc["uid"], "granted": granted}


def revoke(authorization: Authorization, args: tuple[str, ...],
           env: Mapping[str, str] | None = None) -> dict[str, object]:
    authorization.require("OPX")
    reg = register(env)
    opx = _opx(reg)
    if len(args) == 1:
        _master_only("revoking an identity", env)
        reg.revoke_identity(opx, args[0], "revoked by OPX")
        return {"uid": args[0], "revoked": "identity"}
    reg.revoke_access(opx, args[0], args[1])
    return {"uid": args[0], "revoked": args[1]}


def _promote(session: Session, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Fast-forward branch TO of one repository of this tree to FROM, on its remote, through the session.

    cgitsync moves a whole tree, and moves ComplexGitSync behind a gate only on `<project>_<branch>`;
    promoting a branch (CGS-ALPHA -> main) is one repository's affair. Only a fast-forward is pushed:
    anything else is refused, never forced. The push uses the session's key for that repository.
    """
    if len(args) != 3:
        raise ValueError("promote takes DIR FROM TO, e.g. promote ComplexGitSync CGS-ALPHA main")
    where, source, target = args
    base = project_root(env).resolve()
    repo = (base / where).resolve()
    if repo != base and base not in repo.parents:
        raise ValueError(f"{where} is not inside this tree ({base})")
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} is not a git repository")
    origin = _git(session, "config", "--get", "remote.origin.url", cwd=repo)
    if _repo_of(origin) not in {repo_path(r) for r in session.grants}:
        raise AccessRefused(f"this session holds no grant for {origin}")
    _git(session, "fetch", "origin", source, target, cwd=repo)
    new = _git(session, "rev-parse", f"refs/remotes/origin/{source}", cwd=repo)
    old = _git(session, "rev-parse", f"refs/remotes/origin/{target}", cwd=repo)
    done: dict[str, object] = {"repo": _repo_of(origin), "from": source, "to": target, "old": old[:12], "new": new[:12]}
    if old == new:
        return {**done, "pushed": False, "reason": "already up to date"}
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", old, new], cwd=repo, env=session.env())
    if ancestor.returncode:
        raise ValueError(f"{target} is not an ancestor of {source}: not a fast-forward, nothing pushed")
    _git(session, "push", "origin", f"{new}:refs/heads/{target}", cwd=repo)
    current = _git(session, "branch", "--show-current", cwd=repo)
    local = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{target}"], cwd=repo,
                           env=session.env(), capture_output=True, text=True)
    if current != target and local.returncode == 0:
        _git(session, "fetch", "origin", f"{target}:{target}", cwd=repo)  # the local branch follows, fast-forward only
    return {**done, "pushed": True, "commits": int(_git(session, "rev-list", "--count", f"{old}..{new}", cwd=repo))}


def login(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    twin, op = args[0], args[1:]
    home = _env(env).get("CGSHOME")
    if home and Path(home).resolve() != project_root(env).resolve():
        # cgitsync obeys CGSHOME: it would act on another tree than the one this register rules.
        raise AccessRefused(f"CGSHOME ({home}) is not the project this register belongs to ({project_root(env)})")
    me = ask_identity(layer)
    path = glyph_path(me.uid, env)
    if not path.exists():
        raise AccessRefused("no GLYPH for this login/password on this machine")
    reg = register(env)
    sync_identities(reg, env)
    with Session(me, reg, path.read_bytes(), twin, layer) as session:
        # TWIN.cgs only for a bare login, in the directory the command was typed in; never in
        # atCGS's own checkout, which is a tracked repository.
        cgs = None
        if not op:
            where = Path(_env(env).get("INIT_CWD") or Path.cwd()).resolve()
            if where == ROOT:
                raise ValueError("a bare login writes TWIN.cgs: run it from another directory than atCGS's root")
            cgs = session.write_cgs(where)
        result: dict[str, object] = {
            "layer": layer, "code": ROLE_CODES[layer], "uid": me.uid, "twin": twin,
            "cgs": str(cgs) if cgs else None,
            # The login only: which repos and keys a session holds is the register's business.
            "agent_keys": len(session.loaded()),
        }
        if op and op[0] == "promote":
            result["promote"] = _promote(session, op[1:], env)
            op = ()
        if op == ("bootstrap",):
            # A bare bootstrap is the level's own command: one rule for the file name (op_levels).
            named = LevelCommand.of(twin, layer)
            if named is None:
                raise ValueError(f"{layer} has no bootstrap command")
            op = tuple(named.split()[1:])
        if op:
            cgitsync = shutil.which("cgitsync")
            if cgitsync is None:
                raise FileNotFoundError("cgitsync is not on PATH: run under Pixi")
            result["cgitsync"] = session.run([cgitsync, *op]).returncode
    result["closed"] = True
    return result


def _git(session: Session, *argv: str, cwd: Path) -> str:
    done = subprocess.run(["git", *argv], cwd=cwd, env=session.env(), capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"git {argv[0]} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout.strip()


def _repo_of(url: str) -> str:
    """`owner/name`, lower-case, of a git remote url (git@host:o/n.git, https://host/o/n)."""
    path = url.split("://", 1)[-1].split(":", 1)[-1] if "://" not in url else url.split("://", 1)[1].split("/", 1)[1]
    return path.strip("/").removesuffix(".git").lower()


def publish(authorization: Authorization, env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Copy the master identity journal to .omniscience, branch CGS-MOLO, from a throwaway worktree.

    The tree's own .omniscience checkout never moves: the branch is written in a worktree that lives
    in a private directory for the length of an OPX session and is removed after it.
    """
    authorization.require("OPX")
    _master_only("publishing the identities", env)
    reg = register(env)
    opx = _opx(reg)
    entries = reg.identity.entries()
    reg.verify_identities(entries)
    head = hashlib.sha256(canonical(entries[-1])).hexdigest()
    path = glyph_path(opx.uid, env)
    if not path.exists():
        raise AccessRefused("no GLYPH for this login/password on this machine")
    omniscience = project_root(env) / ".omniscience"
    if not (omniscience / ".git").exists():
        raise ValueError(f"no {omniscience} checkout to publish through")
    with Session(opx, reg, path.read_bytes(), "publish", "OPX") as session:
        origin = _git(session, "config", "--get", "remote.origin.url", cwd=omniscience)  # raw, not rewritten
        if _repo_of(origin) not in {repo_path(repo) for repo in session.grants}:
            raise AccessRefused(f"OPX holds no grant for {origin}")
        work = Path(tempfile.mkdtemp(prefix="atcgs-publish-"))
        tree = work / "omniscience"
        try:
            _git(session, "worktree", "prune", cwd=omniscience)
            _git(session, "fetch", "origin", cwd=omniscience)
            known = bool(_git(session, "branch", "-r", "--list", f"origin/{PUBLISH_BRANCH}", cwd=omniscience))
            _git(session, "worktree", "add", "--detach", str(tree), f"origin/{PUBLISH_BRANCH if known else 'main'}",
                 cwd=omniscience)
            target = tree / "atcgs"
            if (target / "identity.head").exists() and (target / "identity.head").read_text().strip() == head:
                return {"published": False, "branch": PUBLISH_BRANCH, "head": head, "reason": "already up to date"}
            target.mkdir(exist_ok=True)
            (target / "identity.jsonl").write_bytes(reg.identity.path.read_bytes())
            (target / "identity.head").write_text(head + "\n", encoding="utf-8")
            _git(session, "add", "atcgs", cwd=tree)
            _git(session, "commit", "-m", f"atcgs identities: {len(entries)} line(s), head {head[:12]}", cwd=tree)
            _git(session, "push", "origin", f"HEAD:refs/heads/{PUBLISH_BRANCH}", cwd=tree)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=omniscience, capture_output=True)
            shutil.rmtree(work, ignore_errors=True)
    return {"published": True, "branch": PUBLISH_BRANCH, "lines": len(entries), "head": head}


def dispatch(req: Request, authorization: Authorization) -> dict[str, object]:
    verb, args = req.args[0], tuple(req.args[1:])
    if verb == "init":
        return init(authorization)
    if verb == "request":
        return request(req.layer, args)
    if verb == "admit":
        return admit(authorization, args)
    if verb == "revoke":
        return revoke(authorization, args)
    if verb == "publish":
        return publish(authorization)
    if verb == "login":
        return login(req.layer, args)
    raise ValueError(f"unknown identity verb: {verb!r}")

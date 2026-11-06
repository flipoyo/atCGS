"""The @cgs identity verbs: request, admit, revoke, login (REFERENCE.md § 6); `init` is atcgs.ownerinit.

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
import sys
import tempfile
from pathlib import Path
from typing import Callable, Mapping

from ComplexGitSync.orchestre.op_levels import LEVELS

from atcgs import PRIVATE, REGISTER_ENV, ROOT, Authorization, Request, Unauthorized, pin
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
    ssh_public,
)
from atcgs.session import AccessRefused, Session, repo_path

OPX_PUB_ENV = "ATCGS_OPX_PUB"  # overrides the pin, for the lab and the tests
GLYPHS_ENV = "ATCGS_GLYPHS"  # where a user's GLYPHs live; default ~/.cgs/.glyph
PROJECT_ENV = "ATCGS_PROJECT"  # act on this project tree from the workspace (OPX onboard); never a user input
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
    """OPX's IDPUB: ATCGS_OPX_PUB, else the key in force in spec/opx.toml (see atcgs.pin)."""
    text = _env(env).get(OPX_PUB_ENV)
    if text is not None:
        pub = base64.b64decode(text, validate=True) if text else None
    else:
        pub = pin.read(ROOT)
    if pub is None:
        raise ValueError("no OPX key is pinned: run `pixi run cgs OPX init`, it pins your key")
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
    forced = _env(env).get(PROJECT_ENV)
    if forced:
        return Path(forced)
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


def _opx(reg: Register, given: Identity | None = None) -> Identity:
    """OPX's identity: the one already derived in this run, else asked (login and password)."""
    opx = given or ask_identity("OPX")
    if opx.pub != reg.opx_pub:
        raise Unauthorized("this login/password is not OPX's pinned key")
    return opx


def _master_only(what: str, env: Mapping[str, str] | None) -> None:
    """Identities are enrolled in the master register only; a project register copies them."""
    if not is_master(env):
        raise Unauthorized(f"{what} is done in the master register (the cgs workspace), then "
                           "`@cgs OPX publish`; this project's register only copies identities")


def _register_form(args: tuple[str, ...]) -> tuple[Path, str, dict[str, str]]:
    """`--register PROJECT=ROLE ... [--name NAME] OUT.toml` -> (OUT, NAME, {PROJECT: ROLE})."""
    ask: dict[str, str] = {}
    name, out, rest = "", None, list(args)
    while rest:
        word = rest.pop(0)
        if word == "--register" and rest:
            project, _, role = rest.pop(0).partition("=")
            if not project or role not in ROLES:
                raise ValueError(f"--register PROJECT=ROLE, with a role of {', '.join(ROLES)}")
            ask[project] = role
        elif word == "--name" and rest:
            name = rest.pop(0)
        elif not word.startswith("--") and out is None:
            out = Path(word)
        else:
            raise ValueError(f"unexpected argument {word!r}: request --register PROJECT=ROLE [--name NAME] OUT.toml")
    if out is None or not ask:
        raise ValueError("request --register PROJECT=ROLE [--register ...] [--name NAME] OUT.toml")
    return out, name, ask


def request_registration(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Ask for the keys of whole projects and write the registration file for the Owner."""
    from atcgs import registration

    out, name, ask = _register_form(args)
    wanted = registration.asked_pairs(ask, ROOT / "examples")
    me = ask_identity(layer, confirm=True)
    keys = [SshKey.generate(repo, role) for repo, role in wanted]
    path = glyph_path(me.uid, env)
    _write_private(path, reseal(me, path.read_bytes() if path.exists() else None, keys))
    proof = me.sign(enrol_statement(me.pub))
    listed = [{"repo": k.repo, "role": k.role, "ssh": k.public} for k in keys]
    out.write_text(registration.render(name, me.uid, me.pub, proof, ask, listed), encoding="utf-8")
    return {"uid": me.uid, "glyph": str(path), "registration": str(out), "ask": ask,
            "keys": [{"repo": k["repo"], "role": k["role"], "fingerprint": fingerprint(k["ssh"])} for k in listed],
            "next": f"send {out} to the Owner, unchanged, and tell them your uid by another channel"}


def request(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    if args and args[0] == "--register" or (args and args[0] == "--name"):
        return request_registration(layer, args, env)
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


def admit_doc(reg: Register, opx: Identity, doc: Mapping[str, object], env: Mapping[str, str] | None = None,
              keys: list[Mapping[str, str]] | None = None) -> list[dict[str, str]]:
    """Enrol (master only) if new, then grant *keys* (default: all of the request) in this register.

    A grant already in the register, same role and same key, is skipped: running it again changes nothing.
    """
    sync_identities(reg, env)
    uid = str(doc["uid"])
    if not reg.state().known(uid):
        _master_only("enrolling a new identity", env)
        reg.enrol(opx, base64.b64decode(str(doc["pub"]), validate=True), base64.b64decode(str(doc["proof"]), validate=True))
    granted = []
    for key in (doc["keys"] if keys is None else keys):  # type: ignore[union-attr]
        held = reg.state().roles(uid).get(key["repo"])
        if held is None:
            reg.grant(opx, uid, key["repo"], key["role"], key["ssh"])
        elif (held.role, held.ssh) != (key["role"], ssh_public(key["ssh"])):
            if held.role != key["role"]:
                raise JournalError(f"{key['repo']}: already granted as {held.role}; revoke it first to change the role")
            reg.rekey(opx, uid, key["repo"], key["role"], key["ssh"])  # same role, a new key: a regenerated GLYPH
        granted.append({"repo": key["repo"], "role": key["role"], "fingerprint": fingerprint(key["ssh"])})
    return granted


def admit(authorization: Authorization, args: tuple[str, ...],
          env: Mapping[str, str] | None = None, who: Identity | None = None) -> dict[str, object]:
    authorization.require("OPX")
    doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    reg = register(env)
    opx = _opx(reg, who)
    return {"uid": doc["uid"], "granted": admit_doc(reg, opx, doc, env)}


def enrol(authorization: Authorization, args: tuple[str, ...],
          env: Mapping[str, str] | None = None, who: Identity | None = None) -> dict[str, object]:
    """Enrol the identity of a request in the master register, and grant nothing.

    A user's access belongs to each twin's own register: `OPX publish`, then `OPX admit REQUEST`
    from that twin's gate, which copies the identity and writes the grants there.
    """
    authorization.require("OPX")
    _master_only("enrolling an identity", env)
    doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    reg = register(env)
    opx = _opx(reg, who)
    if reg.state().known(doc["uid"]):
        return {"uid": doc["uid"], "enrolled": False, "reason": "already known"}
    reg.enrol(opx, base64.b64decode(doc["pub"], validate=True), base64.b64decode(doc["proof"], validate=True))
    return {"uid": doc["uid"], "enrolled": True, "next": "OPX publish, then OPX admit REQUEST from the twin's gate"}


def revoke(authorization: Authorization, args: tuple[str, ...],
           env: Mapping[str, str] | None = None, who: Identity | None = None) -> dict[str, object]:
    authorization.require("OPX")
    reg = register(env)
    opx = _opx(reg, who)
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


def tests_before_push(root: Path, env: Mapping[str, str] | None = None) -> None:
    """The alpha series has one branch: a push of atCGS itself is refused while its tests fail.

    Only where atCGS is the root of the tree (the workspace) and has a tests/ folder; `ATCGS_SKIP_TESTS=1` skips it.
    """
    if _env(env).get("ATCGS_SKIP_TESTS") or not (root / "tests").is_dir() or root.resolve() != ROOT.resolve():
        return
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "tests"], cwd=root, capture_output=True, text=True)
    if done.returncode:
        tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-6:])
        raise ValueError(f"push refused: the tests of atCGS fail on CGS-ALPHA (ATCGS_SKIP_TESTS=1 skips this)\n{tail}")


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
        if op and op[0] == "push":
            tests_before_push(project_root(env), env)
        if op and op[0] == "promote":
            result["promote"] = _promote(session, op[1:], env)
            op = ()
        if op == ("bootstrap",):
            # There is no level file any more: the workspace is examples/cgs-alpha.cgs, installed by `OPX init`.
            raise ValueError("a bare bootstrap needs a file: pixi run cgs OPX login TWIN bootstrap examples/cgs-alpha.cgs TWIN")
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


def publish(authorization: Authorization, env: Mapping[str, str] | None = None,
            who: Identity | None = None) -> dict[str, object]:
    """Copy the master identity journal to .omniscience, branch CGS-MOLO, from a throwaway worktree.

    The tree's own .omniscience checkout never moves: the branch is written in a worktree that lives
    in a private directory for the length of an OPX session and is removed after it.
    """
    authorization.require("OPX")
    _master_only("publishing the identities", env)
    reg = register(env)
    opx = _opx(reg, who)
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


def user_credential(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    """`user-credential [--json] [--probe] [--tree PATH]...`: what atCGS knows of this login, read only."""
    from atcgs import credential

    flags, extra, rest = set(), [], list(args)
    while rest:
        word = rest.pop(0)
        if word in ("--json", "--probe"):
            flags.add(word)
        elif word == "--tree" and rest:
            extra.append(Path(rest.pop(0)).expanduser())
        else:
            raise ValueError("user-credential [--json] [--probe] [--tree PATH]...")
    me = ask_identity(layer)
    path = glyph_path(me.uid, env)
    trees = [(p.name, p) for p in extra] if extra else credential.discover()
    report = credential.collect(me, path.read_bytes() if path.exists() else None, trees, opx_pub(env),
                                credential.probe_github if "--probe" in flags else None)
    report["glyph"]["path"] = str(path)  # type: ignore[index]
    if "--json" in flags:
        return {**report, "__exit__": 0 if report["ok"] else 1}
    return {"__text__": credential.render(report), "__exit__": 0 if report["ok"] else 1}


REGISTRATION_ENV = "ATCGS_REGISTRATION"  # the Owner's folder of received registration files
INTAKE_ENV = "ATCGS_INTAKE"  # where `OPX intake` writes the day's list


def _folder(variable: str, name: str, given: tuple[str, ...] = ()) -> Path:
    if given:
        return Path(given[0]).expanduser()
    return Path(os.environ.get(variable) or Path.home() / ".cgs" / name)


def dispatch(req: Request, authorization: Authorization) -> dict[str, object]:
    verb, args = req.args[0], tuple(req.args[1:])
    if verb == "init":
        from atcgs import ownerinit
        return ownerinit.run(authorization, args)
    if verb == "request":
        return request(req.layer, args)
    if verb == "admit":
        return admit(authorization, args)
    if verb == "enrol":
        return enrol(authorization, args)
    if verb == "revoke":
        return revoke(authorization, args)
    if verb == "publish":
        return publish(authorization)
    if verb == "user-credential":
        return user_credential(req.layer, args)
    if verb == "generate-glyph":
        from atcgs import glyphgen
        return glyphgen.run(req.layer, args)
    if verb == "intake":
        from atcgs import registration
        return registration.intake(_folder(REGISTRATION_ENV, "registration", args[:1]), _folder(INTAKE_ENV, "intake"),
                                   ROOT / "examples")
    if verb == "onboard":
        from atcgs import onboard
        listed = next(a for a in args if not a.startswith("--"))
        return onboard.run(authorization, Path(listed), plan_only="--plan" in args)
    if verb == "login":
        return login(req.layer, args)
    raise ValueError(f"unknown identity verb: {verb!r}")

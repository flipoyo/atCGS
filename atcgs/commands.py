"""The @cgs identity verbs: init, request, admit, revoke, login (README § 3).

Logins and passwords are asked with getpass: never read from argv, the
environment or a file, and never printed. Outputs carry UIDs, public keys,
fingerprints and paths only.
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import shutil
import tomllib
from pathlib import Path
from typing import Callable, Mapping

from ComplexGitSync.orchestre.op_levels import LEVELS, LevelCommand

from atcgs import PRIVATE, REGISTER_ENV, ROOT, Authorization, Request, Unauthorized
from atcgs.glyph import SshKey, reseal
from atcgs.identity import Identity, derive
from atcgs.journal import ROLES, Register, enrol_statement, fingerprint
from atcgs.session import AccessRefused, Session

OPX_PUB_ENV = "ATCGS_OPX_PUB"  # overrides the pin, for the lab and the tests
GLYPHS_ENV = "ATCGS_GLYPHS"  # where a user's GLYPHs live; default ~/.cgs/.glyph
INSTALL_OPS = frozenset({"bootstrap", "initialise"})
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


def register(env: Mapping[str, str] | None = None) -> Register:
    """atCGS's register: .cgitsync/.memory/.register, unless ATCGS_REGISTER names another directory."""
    directory = _env(env).get(REGISTER_ENV)
    if not directory and not (ROOT / PRIVATE / ".memory").is_dir():
        raise ValueError(f"no {PRIVATE}/.memory mount here for the register: mount it (OPX tree) or set {REGISTER_ENV}")
    return Register(Path(directory) if directory else REGISTER, opx_pub(env))


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


def init(authorization: Authorization, env: Mapping[str, str] | None = None) -> dict[str, object]:
    authorization.require("OPX")
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
    if not reg.state().known(doc["uid"]):
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
        reg.revoke_identity(opx, args[0], "revoked by OPX")
        return {"uid": args[0], "revoked": "identity"}
    reg.revoke_access(opx, args[0], args[1])
    return {"uid": args[0], "revoked": args[1]}


def login(layer: str, args: tuple[str, ...], env: Mapping[str, str] | None = None) -> dict[str, object]:
    twin, op = args[0], args[1:]
    me = ask_identity(layer)
    path = glyph_path(me.uid, env)
    if not path.exists():
        raise AccessRefused("no GLYPH for this login/password on this machine")
    with Session(me, register(env), path.read_bytes(), twin, layer) as session:
        # TWIN.cgs only where it is the way in: alone, or for bootstrap/initialise.
        # Run inside an existing tree (commit, push ...), it would be a stray file in a repo.
        cgs = session.write_cgs(Path.cwd()) if not op or op[0] in INSTALL_OPS else None
        result: dict[str, object] = {
            "layer": layer, "code": ROLE_CODES[layer], "uid": me.uid, "twin": twin,
            "cgs": str(cgs) if cgs else None,
            # The login only: which repos and keys a session holds is the register's business.
            "agent_keys": len(session.loaded()),
        }
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
    if verb == "login":
        return login(req.layer, args)
    raise ValueError(f"unknown identity verb: {verb!r}")

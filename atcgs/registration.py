"""The registration file a newcomer sends to the Owner, and the day's list built from them.

    request --register PROJECT=ROLE ...  writes   registration.toml   (public data only)
    OPX intake                           reads    ~/.cgs/registration/*.toml
                                         writes   ~/.cgs/intake/<date>.toml

A registration holds a name, the uid, what is asked per project, and the request itself
(public key, proof of possession, the public halves of the ssh keys). Nothing secret.
The role a person is asked for in a project is a *template* applied to the project's
`.cgs`: every repository gets the role, except atCGS and omniscience, which are USR.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from atcgs.identity import uid_of, verify
from atcgs.journal import ROLES, enrol_statement, ssh_public
from atcgs.session import repo_path

FORMAT = "atcgs-registration/1"
OPEN_REPOS = frozenset({"atcgs", "omniscience"})  # the gate and the identities: USR for everyone
_BARE = re.compile(r"[A-Za-z0-9_-]+")

HEADER = """\
# atCGS registration. Send this file, unchanged, to the Owner.
# It holds only public data: your uid, your public key, the public halves of your ssh keys.
# Tell the Owner your uid by another channel (a call): it is how they know this file is yours.
"""


class RegistrationError(ValueError):
    """A registration file or a list that cannot be used; the message says why."""


def _q(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _key(text: str) -> str:
    return text if _BARE.fullmatch(text) else _q(text)


def _table(mapping: Mapping[str, str]) -> str:
    return "{ " + ", ".join(f"{_key(k)} = {_q(v)}" for k, v in mapping.items()) + " }"


# --- the role template -------------------------------------------------------------------

def project_file(project: str, examples: Path) -> Path:
    """The `.cgs` file that declares the project, found by the project's name."""
    for path in sorted(Path(examples).glob("*.cgs")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if data.get("project", {}).get("name") == project:
            return path
    raise RegistrationError(f"no project {project!r} among the .cgs files of {examples}")


def project_repos(project: str, examples: Path) -> list[str]:
    """The repositories a project's `.cgs` declares."""
    data = tomllib.loads(project_file(project, examples).read_text(encoding="utf-8"))
    return [str(r["repository"]) for r in data.get("repos", []) if "repository" in r]


def template(project: str, role: str, examples: Path) -> list[tuple[str, str]]:
    """(repository, role) for every repository of the project, for a person asking *role*."""
    if role not in ROLES:
        raise RegistrationError(f"a role is one of {', '.join(ROLES)}, not {role!r}")
    return [(repo, "USR" if repo_path(repo).rsplit("/", 1)[-1] in OPEN_REPOS else role)
            for repo in project_repos(project, examples)]


def asked_pairs(ask: Mapping[str, str], examples: Path) -> list[tuple[str, str]]:
    """The union of the templates of what is asked, in order, without duplicates."""
    pairs: list[tuple[str, str]] = []
    for project, role in ask.items():
        for pair in template(project, role, examples):
            if pair not in pairs:
                pairs.append(pair)
    return pairs


# --- the registration file ---------------------------------------------------------------

@dataclass(frozen=True)
class Registration:
    path: Path
    sha256: str
    name: str
    uid: str
    created: str
    ask: dict[str, str]
    pub: bytes
    proof: bytes
    keys: list[dict[str, str]]

    def request_doc(self) -> dict[str, object]:
        """The same document `request` writes as JSON, which `admit` and `enrol` read."""
        return {"uid": self.uid, "pub": base64.b64encode(self.pub).decode(),
                "proof": base64.b64encode(self.proof).decode(), "keys": self.keys}

    def key_for(self, repo: str, role: str) -> dict[str, str] | None:
        return next((k for k in self.keys if repo_path(k["repo"]) == repo_path(repo) and k["role"] == role), None)


def render(name: str, uid: str, pub: bytes, proof: bytes, ask: Mapping[str, str],
           keys: Sequence[Mapping[str, str]], created: datetime.datetime | None = None) -> str:
    when = (created or datetime.datetime.now(datetime.timezone.utc)).replace(microsecond=0, tzinfo=None)
    lines = [HEADER.rstrip("\n"), f"format  = {_q(FORMAT)}", f"name    = {_q(name)}", f"uid     = {_q(uid)}",
             f"created = {when.isoformat()}Z", "", "[ask]"]
    lines += [f"{_key(project)} = {_q(role)}" for project, role in ask.items()]
    lines += ["", "[request]", f"pub   = {_q(base64.b64encode(pub).decode())}",
              f"proof = {_q(base64.b64encode(proof).decode())}", "keys  = ["]
    lines += [f"  {{ repo = {_q(k['repo'])}, role = {_q(k['role'])}, ssh = {_q(k['ssh'])} }}," for k in keys]
    return "\n".join([*lines, "]", ""])


def read(path: Path) -> Registration:
    """Parse and verify a registration: format, uid = sha256(pub), proof of possession, ssh keys."""
    path = Path(path).expanduser()
    raw = path.read_bytes()
    try:
        data = tomllib.loads(raw.decode("utf-8"))
        if data["format"] != FORMAT:
            raise RegistrationError(f"{path.name}: format {data['format']!r}, expected {FORMAT!r}")
        ask = {str(k): str(v) for k, v in data["ask"].items()}
        request = data["request"]
        pub = base64.b64decode(request["pub"], validate=True)
        proof = base64.b64decode(request["proof"], validate=True)
        keys = [{"repo": str(k["repo"]), "role": str(k["role"]), "ssh": ssh_public(str(k["ssh"]))}
                for k in request["keys"]]
        uid, name, created = str(data["uid"]), str(data.get("name", "")), str(data.get("created", ""))
    except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        if isinstance(exc, RegistrationError):
            raise
        raise RegistrationError(f"{path.name}: malformed ({type(exc).__name__}: {exc})") from None
    if not ask or not keys:
        raise RegistrationError(f"{path.name}: nothing asked")
    if uid_of(pub) != uid:
        raise RegistrationError(f"{path.name}: the uid is not sha256 of the public key")
    if not verify(pub, proof, enrol_statement(pub)):
        raise RegistrationError(f"{path.name}: the proof of possession does not verify")
    if any(k["role"] not in ROLES for k in keys):
        raise RegistrationError(f"{path.name}: a key names an unknown role")
    return Registration(path, hashlib.sha256(raw).hexdigest(), name, uid, created, ask, pub, proof, keys)


def check(reg: Registration, grant: Mapping[str, str], examples: Path) -> list[tuple[str, str]]:
    """The (repository, role) pairs *grant* needs; every one must have its key in the registration."""
    needed = asked_pairs(grant, examples)
    missing = [f"{repo} {role}" for repo, role in needed if reg.key_for(repo, role) is None]
    if missing:
        raise RegistrationError(f"{reg.path.name}: no key for {', '.join(missing)}")
    return needed


def check_asked(reg: Registration, examples: Path) -> None:
    """What was asked must match its templates exactly: a missing key or an extra one is refused."""
    needed = check(reg, reg.ask, examples)
    allowed = {(repo_path(repo), role) for repo, role in needed}
    extra = [f"{k['repo']} {k['role']}" for k in reg.keys if (repo_path(k["repo"]), k["role"]) not in allowed]
    if extra:
        raise RegistrationError(f"{reg.path.name}: keys beyond what was asked: {', '.join(extra)}")


# --- the day's list ----------------------------------------------------------------------

def read_list(path: Path) -> dict[str, object]:
    path = Path(path).expanduser()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RegistrationError(f"{path}: {exc}") from None
    persons = data.get("person", [])
    for person in persons:
        for field in ("name", "registration", "sha256", "uid", "grant"):
            if field not in person:
                raise RegistrationError(f"{path.name}: a person has no {field!r}")
    return {"date": data.get("date"), "person": persons,
            "project": {k: dict(v) for k, v in data.get("project", {}).items()}}


def render_list(date: datetime.date, persons: Sequence[Mapping[str, object]],
                projects: Mapping[str, Mapping[str, str]]) -> str:
    lines = [f"# {date}.toml: built by `OPX intake` from the registration folder.",
             "# Check each uid with the person (by phone), then set confirmed = true.",
             "# You may change a role in `grant`; the registration file must still hold the keys for it.",
             f"date = {date.isoformat()}", ""]
    for person in persons:
        lines += ["[[person]]", f"name         = {_q(str(person['name']))}",
                  f"registration = {_q(str(person['registration']))}",
                  f"sha256       = {_q(str(person['sha256']))}   # of the file as intake read it",
                  f"uid          = {_q(str(person['uid']))}",
                  f"confirmed    = {'true' if person.get('confirmed') else 'false'}",
                  f"grant        = {_table(person['grant'])}", ""]  # type: ignore[arg-type]
    for project, values in projects.items():
        lines += [f"[project.{_key(project)}]"] + [f"{k} = {_q(v)}" for k, v in values.items()] + [""]
    return "\n".join(lines)


def intake(folder: Path, out_dir: Path, examples: Path, today: datetime.date | None = None) -> dict[str, object]:
    """Read every registration of *folder*, write the day's list; return a summary with the problems."""
    folder, out_dir = Path(folder).expanduser(), Path(out_dir).expanduser()
    today = today or datetime.date.today()
    target = out_dir / f"{today.isoformat()}.toml"
    kept: dict[str, dict] = {}
    projects: dict[str, dict[str, str]] = {}
    if target.exists():
        old = read_list(target)
        projects = old["project"]  # type: ignore[assignment]
        kept = {p["uid"]: p for p in old["person"]}  # type: ignore[union-attr]
    persons, problems = [], []
    for path in sorted(folder.glob("*.toml")):
        try:
            reg = read(path)
            check_asked(reg, examples)
        except RegistrationError as exc:
            problems.append(str(exc))
            continue
        if any(p["uid"] == reg.uid for p in persons):
            problems.append(f"{path.name}: the uid {reg.uid[:12]}… is already in another file")
            continue
        before = kept.get(reg.uid)
        same = before is not None and before.get("sha256") == reg.sha256
        persons.append({"name": reg.name or path.stem, "registration": str(path), "sha256": reg.sha256,
                        "uid": reg.uid, "confirmed": bool(same and before.get("confirmed")),  # type: ignore[union-attr]
                        "grant": dict(before["grant"]) if same else dict(reg.ask)})  # type: ignore[index]
    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(render_list(today, persons, projects), encoding="utf-8")
    return {"list": str(target), "persons": len(persons), "confirmed": sum(bool(p["confirmed"]) for p in persons),
            "problems": problems}

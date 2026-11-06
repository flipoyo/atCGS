"""The identity and access journals (REFERENCE.md § 6 and § 3.4).

Two JSON-lines files in one register directory, append-only and hash-chained:

    identity.jsonl  enrol | rotate | revoke       who exists
    access.jsonl    grant | revoke                who may do what, where

Every entry is signed by one key and carries `prev = sha256(previous entry)`.
Reading replays the whole file and refuses it at the first bad link,
signature or rule: there is no partial trust. Writing replays the history
with the new entry first, so an entry that would be refused is never written.

The journals hold UIDs, public keys and signatures only: no login, no name,
no password, no private key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from atcgs.identity import Identity, uid_of, verify

ZERO = "0" * 64
ROLES = ("OPX", "DEV", "USR")  # PUB is the absence of a grant
IDENTITY_OPS = ("enrol", "rotate", "revoke")
ACCESS_OPS = ("grant", "revoke")
_ENTRY_KEYS = {"seq", "prev", "op", "uid", "body", "signer", "sig"}
_HEX64 = re.compile(r"[0-9a-f]{64}")
_REPO = re.compile(r"(github:|https://)[A-Za-z0-9_.\-/]+")


class JournalError(ValueError):
    """A journal is refused as a whole; the message says at which entry and why."""


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def enrol_statement(pub: bytes) -> bytes:
    """What a new user signs with IDSK to prove possession of IDPUB."""
    return b"atCGS/enrol/v1\n" + pub


def rotate_statement(old_uid: str, new_pub: bytes) -> bytes:
    """What the new key signs to accept the old UID's history."""
    return b"atCGS/rotate/v1\n" + old_uid.encode() + b"\n" + new_pub


def _signable(kind: str, entry: dict) -> bytes:
    return f"atCGS/journal/v1/{kind}\n".encode() + canonical({k: v for k, v in entry.items() if k != "sig"})


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _unb64(text: object, what: str) -> bytes:
    try:
        return base64.b64decode(str(text), validate=True)
    except ValueError:
        raise JournalError(f"{what} is not base64") from None


def ssh_public(text: str) -> str:
    """Normalise an OpenSSH Ed25519 public key to `ssh-ed25519 <base64>`, comment dropped."""
    parts = text.split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise JournalError("an ssh key must be an ssh-ed25519 public key")
    blob = _unb64(parts[1], "ssh key")
    if not blob.startswith(b"\x00\x00\x00\x0bssh-ed25519"):
        raise JournalError("an ssh key must be an ssh-ed25519 public key")
    return f"ssh-ed25519 {parts[1]}"


def fingerprint(ssh_pub: str) -> str:
    """The SHA256 fingerprint, as `ssh-add -l` and `ssh-keygen -l` print it."""
    blob = base64.b64decode(ssh_public(ssh_pub).split()[1])
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


@dataclass(frozen=True, slots=True)
class Grant:
    repo: str
    role: str
    ssh: str

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.ssh)


@dataclass
class State:
    """What the two journals say, once both are verified."""

    opx: str
    active: dict[str, bytes] = field(default_factory=dict)  # UID -> IDPUB
    origin: dict[str, str] = field(default_factory=dict)  # UID -> first UID of its rotation line
    retired: set[str] = field(default_factory=set)  # rotated away or revoked
    grants: dict[tuple[str, str], Grant] = field(default_factory=dict)  # (origin UID, repo)

    def known(self, uid: str) -> bool:
        return uid in self.origin

    def is_active(self, uid: str) -> bool:
        return uid in self.active

    def roles(self, uid: str) -> dict[str, Grant]:
        """The grants of an active UID, by repo; an empty map means PUB everywhere."""
        if not self.is_active(uid):
            return {}
        line = self.origin[uid]
        return {repo: grant for (owner, repo), grant in self.grants.items() if owner == line}

    def role(self, uid: str, repo: str) -> str:
        grant = self.roles(uid).get(repo)
        return grant.role if grant else "PUB"


class Journal:
    """One append-only, hash-chained JSON-lines file."""

    def __init__(self, path: Path, kind: str) -> None:
        if kind not in ("identity", "access"):
            raise ValueError(f"unknown journal kind: {kind!r}")
        self.path, self.kind = path, kind

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        entries = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                raise JournalError(f"{self.kind} entry {number}: not JSON") from None
            if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
                raise JournalError(f"{self.kind} entry {number}: wrong fields")
            entries.append(entry)
        return entries

    def draft(self, entries: list[dict], op: str, uid: str, body: dict, signer: Identity) -> dict:
        entry = {
            "seq": len(entries) + 1,
            "prev": hashlib.sha256(canonical(entries[-1])).hexdigest() if entries else ZERO,
            "op": op, "uid": uid, "body": body, "signer": signer.uid,
        }
        entry["sig"] = _b64(signer.sign(_signable(self.kind, entry)))
        return entry

    def write(self, entries: Iterable[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        draft = self.path.with_name(f".{self.path.name}.tmp")
        draft.write_text("".join(canonical(e).decode() + "\n" for e in entries), encoding="utf-8")
        os.replace(draft, self.path)


def _check_link(kind: str, entries: list[dict], index: int) -> dict:
    entry = entries[index]
    if entry["seq"] != index + 1:
        raise JournalError(f"{kind} entry {index + 1}: out of sequence")
    prev = hashlib.sha256(canonical(entries[index - 1])).hexdigest() if index else ZERO
    if entry["prev"] != prev:
        raise JournalError(f"{kind} entry {index + 1}: broken chain")
    if not isinstance(entry["body"], dict) or not _HEX64.fullmatch(str(entry["uid"])):
        raise JournalError(f"{kind} entry {index + 1}: malformed")
    return entry


def _check_sig(kind: str, entry: dict, pub: bytes | None) -> None:
    if pub is None or uid_of(pub) != entry["signer"]:
        raise JournalError(f"{kind} entry {entry['seq']}: signer not allowed")
    if not verify(pub, _unb64(entry["sig"], "signature"), _signable(kind, entry)):
        raise JournalError(f"{kind} entry {entry['seq']}: bad signature")


def _pub(body: dict, key: str, where: str) -> bytes:
    raw = _unb64(body.get(key), where)
    if len(raw) != 32:
        raise JournalError(f"{where}: an IDPUB is 32 bytes")
    return raw


def _replay_identity(entries: list[dict], opx_pub: bytes) -> State:
    state = State(opx=uid_of(opx_pub))
    for index in range(len(entries)):
        entry = _check_link("identity", entries, index)
        op, uid, body, where = entry["op"], entry["uid"], entry["body"], f"identity entry {index + 1}"
        if index == 0 and not (op == "enrol" and uid == state.opx):
            raise JournalError(f"{where}: the journal must open with OPX's own enrol")
        if op == "enrol":
            pub = _pub(body, "pub", where)
            if uid_of(pub) != uid or state.known(uid):
                raise JournalError(f"{where}: UID mismatch or already known")
            if not verify(pub, _unb64(body.get("proof"), where), enrol_statement(pub)):
                raise JournalError(f"{where}: no proof of possession")
            _check_sig("identity", entry, opx_pub)
            state.active[uid], state.origin[uid] = pub, uid
        elif op == "rotate":
            new_pub = _pub(body, "pub", where)
            new_uid = uid_of(new_pub)
            if uid == state.opx or not state.is_active(uid) or state.known(new_uid):
                raise JournalError(f"{where}: cannot rotate this UID")
            if not verify(new_pub, _unb64(body.get("proof"), where), rotate_statement(uid, new_pub)):
                raise JournalError(f"{where}: the new key did not sign the rotation")
            _check_sig("identity", entry, state.active[uid])
            state.active[new_uid], state.origin[new_uid] = new_pub, state.origin[uid]
            del state.active[uid]
            state.retired.add(uid)
        elif op == "revoke":
            if uid == state.opx or not state.is_active(uid):
                raise JournalError(f"{where}: cannot revoke this UID")
            signer = opx_pub if entry["signer"] == state.opx else state.active[uid]
            _check_sig("identity", entry, signer)
            del state.active[uid]
            state.retired.add(uid)
        else:
            raise JournalError(f"{where}: unknown op {op!r}")
    return state


def _replay_access(entries: list[dict], opx_pub: bytes, state: State) -> None:
    for index in range(len(entries)):
        entry = _check_link("access", entries, index)
        op, uid, body, where = entry["op"], entry["uid"], entry["body"], f"access entry {index + 1}"
        _check_sig("access", entry, opx_pub)
        if not state.known(uid):
            raise JournalError(f"{where}: unknown UID")
        repo = body.get("repo")
        if not isinstance(repo, str) or not _REPO.fullmatch(repo):
            raise JournalError(f"{where}: invalid repo")
        key = (state.origin[uid], repo)
        if op == "grant":
            if body.get("role") not in ROLES or key in state.grants:
                raise JournalError(f"{where}: invalid role, or the repo is already granted")
            ssh = ssh_public(str(body.get("ssh", "")))
            if any(grant.ssh == ssh for grant in state.grants.values()):
                raise JournalError(f"{where}: this ssh key is already granted")
            state.grants[key] = Grant(repo, body["role"], ssh)
        elif op == "revoke":
            if key not in state.grants:
                raise JournalError(f"{where}: nothing to revoke")
            del state.grants[key]
        else:
            raise JournalError(f"{where}: unknown op {op!r}")


class Register:
    """The register directory holding both journals; OPX's public key is the root of trust."""

    def __init__(self, directory: Path, opx_pub: bytes) -> None:
        self.directory, self.opx_pub = Path(directory), opx_pub
        self.identity = Journal(self.directory / "identity.jsonl", "identity")
        self.access = Journal(self.directory / "access.jsonl", "access")

    def state(self) -> State:
        state = _replay_identity(self.identity.entries(), self.opx_pub)
        _replay_access(self.access.entries(), self.opx_pub, state)
        return state

    def verify_identities(self, entries: list[dict]) -> State:
        """Replay *entries* as an identity journal against the pinned OPX key; JournalError if it fails."""
        return _replay_identity(entries, self.opx_pub)

    def _append(self, journal: Journal, op: str, uid: str, body: dict, signer: Identity) -> dict:
        entries = journal.entries()
        entries.append(journal.draft(entries, op, uid, body, signer))
        identity = entries if journal is self.identity else self.identity.entries()
        access = entries if journal is self.access else self.access.entries()
        _replay_access(access, self.opx_pub, _replay_identity(identity, self.opx_pub))
        journal.write(entries)
        return entries[-1]

    # identity journal
    def init(self, opx: Identity) -> dict:
        """OPX enrols itself: the first entry, and only with the pinned key."""
        if opx.pub != self.opx_pub:
            raise JournalError("this OPX key is not the pinned one")
        return self.enrol(opx, opx.pub, opx.sign(enrol_statement(opx.pub)))

    def enrol(self, opx: Identity, pub: bytes, proof: bytes) -> dict:
        return self._append(self.identity, "enrol", uid_of(pub), {"pub": _b64(pub), "proof": _b64(proof)}, opx)

    def rotate(self, old: Identity, new: Identity) -> dict:
        proof = new.sign(rotate_statement(old.uid, new.pub))
        return self._append(self.identity, "rotate", old.uid, {"pub": _b64(new.pub), "proof": _b64(proof)}, old)

    def revoke_identity(self, signer: Identity, uid: str, reason: str = "") -> dict:
        return self._append(self.identity, "revoke", uid, {"reason": reason}, signer)

    # access journal
    def grant(self, opx: Identity, uid: str, repo: str, role: str, ssh: str) -> dict:
        state = self.state()
        if not state.is_active(uid):
            raise JournalError("only an active UID can be granted")
        body = {"repo": repo, "role": role, "ssh": ssh_public(ssh)}
        return self._append(self.access, "grant", uid, body, opx)

    def rekey(self, opx: Identity, uid: str, repo: str, role: str, ssh: str) -> None:
        """Replace the key of an existing grant: a revoke and a grant, written together or not at all."""
        entries = self.access.entries()
        for op, body in (("revoke", {"repo": repo}), ("grant", {"repo": repo, "role": role, "ssh": ssh_public(ssh)})):
            entries.append(self.access.draft(entries, op, uid, body, opx))
        _replay_access(entries, self.opx_pub, _replay_identity(self.identity.entries(), self.opx_pub))
        self.access.write(entries)

    def revoke_access(self, opx: Identity, uid: str, repo: str) -> dict:
        return self._append(self.access, "revoke", uid, {"repo": repo}, opx)

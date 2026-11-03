#!/usr/bin/env python3
"""IdentityJournals M0: the whole identity flow on throwaway data, step by step.

    pixi run identity-demo [--pbm-dir DIR]

Everything lives in a temporary directory deleted at the end: no network, no
~/.ssh, no real register. --pbm-dir also writes each GLYPH as a 256x256 image.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atcgs import require_pixi  # noqa: E402
from atcgs.glyph import GlyphError, SshKey, seal, to_pbm  # noqa: E402
from atcgs.identity import Identity, derive, profile_from_env  # noqa: E402
from atcgs.journal import JournalError, Register, enrol_statement, fingerprint  # noqa: E402
from atcgs.session import AccessRefused, Session  # noqa: E402

REPO = "github:flipoyo/demo"
# Demo credentials: they exist only in this file and in memory.
CREDENTIALS = {
    "opx": ("opx", "opx demo passphrase, long enough"),
    "alice": ("alice", "alice demo passphrase, long enough"),
    "bob": ("bob", "bob demo passphrase, long enough"),
}
ROLES = {"alice": "DEV", "bob": "USR"}


@dataclass
class Lab:
    directory: Path
    ids: dict[str, Identity]
    register: Register
    keys: dict[str, SshKey]

    def glyph(self, who: str) -> Path:
        return self.directory / "glyphs" / f"{who}.glyph"


def step(number: object, title: str) -> None:
    print(f"\n== {number}. {title}")


def build_lab(directory: Path, repo: str = REPO, verbose: bool = True) -> Lab:
    """Steps 1 to 3: OPX and two users, both journals, one sealed GLYPH each."""
    say = print if verbose else (lambda *_: None)
    ids = {who: derive(*cred) for who, cred in CREDENTIALS.items()}
    opx = ids["opx"]
    register = Register(directory / "register", opx.pub)
    register.init(opx)
    keys = {}
    (directory / "glyphs").mkdir()
    for who, role in ROLES.items():
        me = ids[who]
        register.enrol(opx, me.pub, me.sign(enrol_statement(me.pub)))
        keys[who] = SshKey.generate(repo, role)
        register.grant(opx, me.uid, repo, role, keys[who].public)
        lab_glyph = seal(me, [keys[who]])
        (directory / "glyphs" / f"{who}.glyph").write_bytes(lab_glyph)
        say(f"   {who:5} UID {me.uid[:16]}…  {role} on {repo}  ssh {fingerprint(keys[who].public)}")
    return Lab(directory, ids, register, keys)


def show_journals(lab: Lab) -> None:
    for journal in (lab.register.identity, lab.register.access):
        print(f"   {journal.path.name}")
        for e in journal.entries():
            body = {k: (v[:16] + "…" if isinstance(v, str) and len(v) > 24 else v) for k, v in e["body"].items()}
            print(f"     {e['seq']} {e['op']:6} uid {e['uid'][:12]}… signer {e['signer'][:12]}…  {body}")
    first = lab.register.identity.path.read_text().splitlines()[0]
    print(f"   one raw entry ({len(first)} bytes): {first[:110]}…")


def show_glyph(lab: Lab, pbm_dir: Path | None) -> None:
    import hashlib

    for who in ROLES:
        data = lab.glyph(who).read_bytes()
        print(f"   {who:5} GLYPH {len(data)} bytes = 256x256 bits, sha256 {hashlib.sha256(data).hexdigest()[:16]}…,"
              f" starts {data[:12].hex()}")
        ones = sum(bin(b).count("1") for b in data[17:])
        print(f"         ones in the sealed part: {ones} of {8 * len(data[17:])} (noise is ~50%)")
        if pbm_dir:
            pbm_dir.mkdir(parents=True, exist_ok=True)
            (pbm_dir / f"{who}.pbm").write_bytes(to_pbm(data))
            print(f"         image: {pbm_dir / f'{who}.pbm'}")


def login(lab: Lab) -> None:
    alice = derive(*CREDENTIALS["alice"])  # recomputed from login + password, as at a real login
    print(f"   derived again: UID {alice.uid[:16]}… (same as at enrol: {alice.uid == lab.ids['alice'].uid})")
    with Session(alice, lab.register, lab.glyph("alice").read_bytes(), "demo", "DEV", lifetime=60) as s:
        loaded = s.loaded()
        granted = s.grants[REPO].fingerprint
        print(f"   journal says DEV on {REPO}, key {granted}")
        print(f"   ssh-add -l in the session's agent: {loaded}")
        print(f"   agent key == granted key: {loaded == [granted]}")
        print("   the .cgs the Twin gets:")
        print("     " + s.cgs().replace("\n", "\n     ").rstrip())
        socket = Path(s.env()["SSH_AUTH_SOCK"])
    step(6, "Close")
    print(f"   agent socket still there: {socket.exists()}; agent directory still there: {socket.parent.exists()}")


def refusals(lab: Lab) -> None:
    def refused(label: str, action) -> None:
        try:
            action()
        except (AccessRefused, GlyphError, JournalError) as exc:
            print(f"   REFUSED  {label}: {type(exc).__name__}: {exc}")
        else:
            print(f"   ACCEPTED {label}  <-- this should not happen")
            raise SystemExit(1)

    glyph = lab.glyph("alice").read_bytes()

    def wrong_password() -> None:
        with Session(derive("alice", "not the password"), lab.register, glyph, "demo", "DEV"):
            pass

    def flipped_bit() -> None:
        bad = bytearray(glyph)
        bad[4000] ^= 0b0001_0000
        with Session(lab.ids["alice"], lab.register, bytes(bad), "demo", "DEV"):
            pass

    def grant_by_alice() -> None:
        journal = lab.register.access
        saved = journal.path.read_bytes()
        entries = journal.entries()
        body = {"repo": REPO, "role": "OPX", "ssh": lab.keys["alice"].public}
        entries.append(journal.draft(entries, "grant", lab.ids["alice"].uid, body, lab.ids["alice"]))
        journal.write(entries)  # written behind the API's back, as an attacker would
        try:
            lab.register.state()
        finally:
            journal.path.write_bytes(saved)

    def bob_after_revoke() -> None:
        lab.register.revoke_access(lab.ids["opx"], lab.ids["bob"].uid, REPO)
        print(f"   (OPX revoked bob on {REPO}; bob's role there is now {lab.register.state().role(lab.ids['bob'].uid, REPO)})")
        with Session(lab.ids["bob"], lab.register, lab.glyph("bob").read_bytes(), "demo", "USR"):
            pass

    refused("wrong password", wrong_password)
    refused("one flipped bit in alice's GLYPH", flipped_bit)
    refused("a grant signed by alice instead of OPX", grant_by_alice)
    refused("bob after revoke", bob_after_revoke)


def no_secret_on_disk(lab: Lab) -> None:
    files = [p for p in lab.directory.rglob("*") if p.is_file()]
    needles = [s.encode() for cred in CREDENTIALS.values() for s in cred]
    needles += [k.private.split("\n")[1].encode() for k in lab.keys.values()]  # a line of each private key
    hits = [str(p.relative_to(lab.directory)) for p in files for n in needles if n in p.read_bytes()]
    print(f"   searched {len(files)} files for {len(needles)} logins, passwords and private-key lines: "
          f"{'none found' if not hits else hits}")
    if hits:
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pbm-dir", type=Path, help="also write each GLYPH as a 256x256 PBM image here")
    args = parser.parse_args()
    require_pixi()
    directory = Path(tempfile.mkdtemp(prefix="cgs-demo-"))
    try:
        print(f"IdentityJournals demo, KDF profile '{profile_from_env()}', in {directory}")
        step(1, "OPX and two users: login + password -> Ed25519 -> UID")
        lab = build_lab(directory)
        step(2, "The journals")
        show_journals(lab)
        step(3, "The GLYPHs: each user's ssh key, sealed")
        show_glyph(lab, args.pbm_dir)
        step(4, "No secret on disk")
        no_secret_on_disk(lab)
        step(5, "alice logs in as DEV")
        login(lab)
        step(7, "Refusals")
        refusals(lab)
    finally:
        shutil.rmtree(directory)
    print(f"\n   temporary directory removed: {not directory.exists()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""IdentityJournals M5: the journals against a real ssh remote, on localhost.

    pixi run local-remote

An unprivileged sshd on 127.0.0.1 serves two bare repositories. Its
authorized_keys is generated from the access journal, as OPX would install
deploy keys: each key opens its own repo only, DEV may push, USR may only
fetch. alice reaches both repos with the session's ssh, each with its own key;
plain ssh offering every agent key is refused, as GitHub would. Then OPX
revokes bob while his session is open, and the remote refuses his key.
Everything lives in a temporary directory deleted at the end.
"""

from __future__ import annotations

import getpass
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from identity_demo import REPO, Lab, build_lab, step  # noqa: E402

OTHER = "github:flipoyo/other"
REPOS = (REPO, OTHER)

from atcgs import require_pixi  # noqa: E402
from atcgs.session import Session, repo_path  # noqa: E402

# The forced command of every key, `gate.sh rw|ro owner/name`: git over ssh only, to the
# key's own repo only (a GitHub deploy key's rule), and receive-pack needs `rw`.
GATE = """#!/bin/sh
path=$(printf %s "${SSH_ORIGINAL_COMMAND#* }" | tr -d "'" | tr 'A-Z' 'a-z'); path=${path%.git}
name=${path##*/}; rest=${path%/*}; owner=${rest##*/}
if [ "$owner/$name" != "$2" ]; then
  echo "atCGS remote: this key is a deploy key of $2, not of $owner/$name" >&2; exit 1
fi
case "$SSH_ORIGINAL_COMMAND" in
  "git-upload-pack "*) exec git-shell -c "$SSH_ORIGINAL_COMMAND" ;;
  "git-receive-pack "*)
    if [ "$1" = rw ]; then exec git-shell -c "$SSH_ORIGINAL_COMMAND"; fi
    echo "atCGS remote: this key is read-only (USR)" >&2; exit 1 ;;
  *) echo "atCGS remote: git over ssh only" >&2; exit 1 ;;
esac
"""
GIT_ID = ["-c", "user.name=demo", "-c", "user.email=demo@example.invalid"]


def need(tool: str) -> str:
    path = shutil.which(tool)
    if path is None:
        raise SystemExit(f"local-remote needs {tool} on PATH")
    return path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def authorized_keys(lab: Lab, gate: Path) -> str:
    """OPX's projection of the access journal onto the remote: one line per active grant."""
    state = lab.register.state()
    lines = []
    for uid in sorted(state.active):
        for grant in state.roles(uid).values():
            mode = "rw" if grant.role in ("OPX", "DEV") else "ro"
            lines.append(f'restrict,command="{gate} {mode} {repo_path(grant.repo)}" {grant.ssh} {grant.role}')
    return "\n".join(lines) + "\n"


class Remote:
    def __init__(self, base: Path, lab: Lab) -> None:
        self.base, self.lab, self.port = base, lab, free_port()
        self.gate = base / "gate.sh"
        self.gate.write_text(GATE)
        self.gate.chmod(0o755)
        self.keys = base / "authorized_keys"
        # Bare repos at <base>/<owner>/<name>.git, so the remote command names owner/name.
        self.repos = {repo: base / f"{repo_path(repo)}.git" for repo in REPOS}
        seed = base / "seed"
        subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
        (seed / "README").write_text("demo\n")
        subprocess.run(["git", "-C", str(seed), *GIT_ID, "commit", "-q", "--allow-empty", "-m", "seed"], check=True)
        for bare in self.repos.values():
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
            subprocess.run(["git", "-C", str(seed), "push", "-q", str(bare), "main"], check=True)
        self.sync()
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(base / "host")], check=True)
        (base / "sshd_config").write_text(
            f"Port {self.port}\nListenAddress 127.0.0.1\nHostKey {base / 'host'}\n"
            f"AuthorizedKeysFile {self.keys}\nPidFile {base / 'sshd.pid'}\nStrictModes no\n"
            "PasswordAuthentication no\nKbdInteractiveAuthentication no\n")
        self.sshd = subprocess.Popen([need("sshd"), "-D", "-e", "-f", str(base / "sshd_config")],
                                     stdout=subprocess.DEVNULL, stderr=(base / "sshd.log").open("w"))
        deadline = time.monotonic() + 5
        while not self._listening():
            if self.sshd.poll() is not None or time.monotonic() > deadline:
                raise SystemExit("sshd did not start:\n" + (base / "sshd.log").read_text())
            time.sleep(0.05)
        self.user = getpass.getuser()

    def url(self, repo: str) -> str:
        return f"ssh://{self.user}@127.0.0.1:{self.port}{self.repos[repo]}"

    def _listening(self) -> bool:
        with socket.socket() as s:
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def sync(self) -> None:
        self.keys.write_text(authorized_keys(self.lab, self.gate))

    def git(self, session: Session, *args: str, plain: bool = False) -> subprocess.CompletedProcess[str]:
        """git through the session's own ssh (one key per repo); `plain`: every agent key in turn."""
        env = session.env()
        ssh = "ssh -F /dev/null -o IdentityFile=none -o BatchMode=yes" if plain else env["GIT_SSH_COMMAND"]
        env["GIT_SSH_COMMAND"] = (f"{ssh} -o StrictHostKeyChecking=accept-new "
                                  f"-o UserKnownHostsFile={self.base / 'known_hosts'}")
        return subprocess.run(["git", *GIT_ID, *args], env=env, capture_output=True, text=True)

    def stop(self) -> None:
        self.sshd.terminate()
        self.sshd.wait(timeout=5)


def report(label: str, result: subprocess.CompletedProcess[str], expect_ok: bool) -> bool:
    ok = result.returncode == 0
    lines = result.stderr.strip().splitlines() or ["?"]
    why = next((line for line in lines if "atCGS" in line or "Permission denied" in line), lines[0])
    reason = "" if ok else f"  <- {why.strip()}"
    verdict = "as expected" if ok == expect_ok else "UNEXPECTED"
    print(f"   {'OK     ' if ok else 'REFUSED'} {label}{reason}   [{verdict}]")
    return ok == expect_ok


def scenario(lab: Lab, remote: Remote) -> bool:
    base, good = remote.base, []
    print("   authorized_keys, generated from the access journal:")
    for line in remote.keys.read_text().splitlines():
        print(f"     {line[:60]}… {line.split()[-1]}")

    step(2, "alice (DEV): two repos, each reached with its own key")
    with Session(lab.ids["alice"], lab.register, lab.glyph("alice").read_bytes(), "demo", "DEV") as s:
        print(f"   alice's agent holds {len(s.loaded())} keys")
        for repo in REPOS:
            work = base / "alice" / repo_path(repo)
            good.append(report(f"clone {repo}", remote.git(s, "clone", "-q", remote.url(repo), str(work)), True))
            (work / "alice.txt").write_text("from alice\n")
            remote.git(s, "-C", str(work), "add", "alice.txt")
            remote.git(s, "-C", str(work), "commit", "-q", "-m", "alice")
            good.append(report(f"push  {repo}", remote.git(s, "-C", str(work), "push", "-q", "origin", "main"), True))
        print("   without the session's ssh, the agent offers its first key to every repo:")
        work = base / "alice" / repo_path(OTHER)
        (work / "again.txt").write_text("again\n")
        remote.git(s, "-C", str(work), "add", "again.txt")
        remote.git(s, "-C", str(work), "commit", "-q", "-m", "again")
        pushed = remote.git(s, "-C", str(work), "push", "-q", "origin", "main", plain=True)
        good.append(report(f"push  {OTHER}, plain ssh", pushed, False))

    step(3, "bob (USR): clone, then push")
    with Session(lab.ids["bob"], lab.register, lab.glyph("bob").read_bytes(), "demo", "USR") as s:
        work = base / "bob"
        good.append(report("clone", remote.git(s, "clone", "-q", remote.url(REPO), str(work)), True))
        print(f"   bob sees alice's commit: {(work / 'alice.txt').exists()}")
        (work / "bob.txt").write_text("from bob\n")
        remote.git(s, "-C", str(work), "add", "bob.txt")
        remote.git(s, "-C", str(work), "commit", "-q", "-m", "bob")
        good.append(report("push", remote.git(s, "-C", str(work), "push", "-q", "origin", "main"), False))

        step(4, "OPX revokes bob while his session is open")
        lab.register.revoke_access(lab.ids["opx"], lab.ids["bob"].uid, REPO)
        remote.sync()
        print(f"   authorized_keys now has {len(remote.keys.read_text().splitlines())} line(s); "
              f"bob's {REPO} key is still in his agent: {len(s.loaded()) == len(REPOS)}")
        good.append(report("fetch with the key still loaded",
                           remote.git(s, "-C", str(work), "fetch", "-q", "origin"), False))
    return all(good)


def main() -> int:
    require_pixi()
    for tool in ("git", "git-shell", "sshd", "ssh", "ssh-keygen"):
        need(tool)
    base = Path(tempfile.mkdtemp(prefix="cgs-remote-"))
    remote = None
    try:
        step(1, "Lab and local remote")
        lab = build_lab(base / "lab", REPOS)
        remote = Remote(base, lab)
        print(f"   sshd on 127.0.0.1:{remote.port}, bare repos {', '.join(repo_path(r) for r in REPOS)}")
        passed = scenario(lab, remote)
    finally:
        if remote:
            remote.stop()
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n   {'all checks passed' if passed else 'SOME CHECKS FAILED'}; temporary directory removed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""A session, from login to an activated Twin (README § 3.6).

    1  login, password       -> IDSK, IDPUB, UID, in memory      (the caller: identity.derive)
    2  identity journal      UID enrolled and not revoked?
    3  proof of possession   IDSK signs (nonce, UID, Twin, time); checked
    4  access journal        the repos where UID holds the requested role
    5  open the GLYPH        the ssh keys of those repos, in memory, matched by fingerprint
    6  ssh-add -t            into a private ssh-agent; no key is ever written to disk
    7  .cgs, cgitsync        git over ssh through that agent only
    8  close                 agent emptied and killed, its directory removed

The agent is the session's own: its socket lives in a fresh 0700 directory and
is handed only to the subprocesses the session runs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Mapping, Sequence

from atcgs.glyph import GlyphError, SshKey, open_glyph
from atcgs.identity import Identity, verify
from atcgs.journal import Grant, Register, canonical, fingerprint

DEFAULT_LIFETIME = 3600  # seconds a key stays in the agent, even if close() never runs
_SOCKET_LIMIT = 90  # Unix socket paths are limited to ~108 bytes

# The session's ssh, given to git as GIT_SSH_COMMAND. A GitHub deploy key is valid for
# one repo only, and ssh offers the agent's keys in turn: GitHub would accept the first
# as a deploy key of *another* repo, then refuse the push. So the wrapper reads the repo
# from git's remote command and offers that repo's key only. -F /dev/null keeps the
# user's ~/.ssh keys and config out: a dogfooded push must prove the GLYPH's keys.
SSH_WRAPPER = """#!/bin/sh
# atCGS session ssh: only the key granted for the repo being reached, nothing from ~/.ssh.
here=$(dirname "$0")
key=""
for arg in "$@"; do
  case "$arg" in
    "git-upload-pack "*|"git-receive-pack "*|"git-upload-archive "*)
      path=$(printf %s "${arg#* }" | tr -d "'" | tr 'A-Z' 'a-z'); path=${path%/}; path=${path%.git}
      name=${path##*/}; rest=${path%/*}; owner=${rest##*/}
      key=$(awk -v r="$owner/$name" '$1 == r { print $2 }' "$here/keys.map") ;;
  esac
done
if [ -z "$key" ]; then
  echo "atCGS session: no key is granted for this repository in this session" >&2; exit 255
fi
exec "@SSH@" -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityFile="$key" \\
  -o IdentityAgent="$here/agent" "$@"
"""


# The grants a session of each level loads: its own, plus the read-only USR ones.
READS = {"OPX": frozenset({"OPX", "USR"}), "DEV": frozenset({"DEV", "USR"}), "USR": frozenset({"USR"})}


class AccessRefused(PermissionError):
    """The journals do not let this UID act as the requested layer."""


def challenge(nonce: bytes, uid: str, twin: str, when: int) -> bytes:
    return b"atCGS/session/v1\n" + canonical({"nonce": nonce.hex(), "uid": uid, "twin": twin, "time": when})


def repo_path(repo: str) -> str:
    """`owner/name`, lower-case, as the remote command names it: github:o/n, https://host/o/n(.git)."""
    path = repo.split(":", 1)[1] if repo.startswith("github:") else repo.split("://", 1)[-1].split("/", 1)[-1]
    parts = path.strip("/").removesuffix(".git").lower().split("/")
    return "/".join(parts[-2:])


def _socket_parent() -> str | None:
    base = tempfile.gettempdir()
    if len(base) < _SOCKET_LIMIT - 30:
        return None
    return "/tmp" if os.path.isdir("/tmp") else None


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"{name} is not on PATH (it comes with openssh in the Pixi environment)")
    return path


class Session:
    """Steps 2 to 8; use it as a context manager."""

    def __init__(self, identity: Identity, register: Register, glyph: bytes, twin: str, layer: str,
                 lifetime: int = DEFAULT_LIFETIME) -> None:
        if layer not in ("OPX", "DEV", "USR"):
            raise AccessRefused(f"{layer} has no ssh access: PUB needs no session")
        self.identity, self.register, self.twin, self.layer = identity, register, twin, layer
        self.lifetime = lifetime
        self.grants: dict[str, Grant] = {}
        self._glyph = glyph
        self._dir: Path | None = None
        self._agent: subprocess.Popen[bytes] | None = None

    # steps 2 to 6
    def __enter__(self) -> Session:
        try:
            self.grants = self._authorise()
            keys = self._keys()
            self._start_agent()
            for key in keys:
                self._add(key)
            self._write_ssh(keys)
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _authorise(self) -> dict[str, Grant]:
        state = self.register.state()
        uid = self.identity.uid
        if not state.is_active(uid):
            raise AccessRefused("this login/password is not enrolled, or was revoked: PUB")
        nonce, when = os.urandom(32), int(time.time())
        statement = challenge(nonce, uid, self.twin, when)
        if not verify(state.active[uid], self.identity.sign(statement), statement):
            raise AccessRefused("proof of possession failed")
        mine = state.roles(uid)
        if not any(g.role == self.layer for g in mine.values()):
            raise AccessRefused(f"this UID holds no {self.layer} grant")
        # A session acts at its level, and also reads what the UID may read: its USR grants
        # (read-only deploy keys), such as a twin's gate repositories for a DEV.
        return {repo: g for repo, g in mine.items() if g.role in READS[self.layer]}

    def _keys(self) -> list[SshKey]:
        held = {(k.repo, fingerprint(k.public)): k for k in open_glyph(self.identity, self._glyph)}
        self._glyph = b""
        keys = []
        for repo, grant in sorted(self.grants.items()):
            key = held.get((repo, grant.fingerprint))
            if key is None:
                raise GlyphError(f"the GLYPH holds no key for {repo} matching the granted one")
            keys.append(key)
        return keys

    def _start_agent(self) -> None:
        self._dir = Path(tempfile.mkdtemp(prefix="cgs-agent-", dir=_socket_parent()))
        socket = self._dir / "agent"
        self._agent = subprocess.Popen([_tool("ssh-agent"), "-D", "-a", str(socket)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 5
        while not socket.exists():
            if self._agent.poll() is not None or time.monotonic() > deadline:
                raise OSError("ssh-agent did not start")
            time.sleep(0.02)

    def _add(self, key: SshKey) -> None:
        subprocess.run([_tool("ssh-add"), "-q", "-t", str(self.lifetime), "-"], input=key.private.encode(),
                       env=self.env(), check=True, capture_output=True)

    def _write_ssh(self, keys: list[SshKey]) -> None:
        """Public halves and the repo -> key map for the wrapper; no private key is written."""
        assert self._dir is not None
        (self._dir / "keys").mkdir(mode=0o700)
        lines = []
        for number, key in enumerate(keys):
            public = self._dir / "keys" / f"{number}.pub"
            public.write_text(key.public + "\n")
            lines.append(f"{repo_path(key.repo)} {public}")
        (self._dir / "keys.map").write_text("\n".join(lines) + "\n")
        wrapper = self._dir / "ssh"
        wrapper.write_text(SSH_WRAPPER.replace("@SSH@", _tool("ssh")))
        wrapper.chmod(0o700)

    # step 7
    def env(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        """The environment for a subprocess: the caller's, with this session's agent only."""
        if self._dir is None:
            raise ValueError("the session is closed")
        env = dict(os.environ if base is None else base)
        env.pop("SSH_AGENT_PID", None)
        env.pop("GIT_SSH", None)
        env["SSH_AUTH_SOCK"] = str(self._dir / "agent")
        env["GIT_SSH_COMMAND"] = str(self._dir / "ssh")
        return env

    def loaded(self) -> list[str]:
        """Fingerprints the agent holds, as `ssh-add -l` prints them."""
        result = subprocess.run([_tool("ssh-add"), "-l"], env=self.env(), capture_output=True, text=True)
        return [line.split()[1] for line in result.stdout.splitlines() if line.strip()] if result.returncode == 0 else []

    def cgs(self) -> str:
        """The `.cgs` of the Twin: the granted repos, over ssh, and nothing else."""
        lines = [
            f"# Written by @cgs {self.layer} login for Twin {self.twin}; no identity is recorded here.",
            f'project = {{ name = "{self.twin}", default_branch = "main", fallback_branch = "main" }}',
            "",
            "repos = [",
        ]
        for repo, grant in sorted(self.grants.items()):
            name = repo.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
            # Write access is the remote's to enforce (README § 3.4), not a .cgs field.
            lines.append(f'    {{ repository = "{repo}", relative_path = "{name}", default_branch = "main", '
                         f'fallback_branch = "main", access_protocol = "ssh" }},  # {grant.role}')
        return "\n".join([*lines, "]", ""])

    def write_cgs(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.twin}.cgs"
        path.write_text(self.cgs(), encoding="utf-8")
        return path

    def run(self, argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(list(argv), cwd=cwd, env=self.env())

    # step 8
    def close(self) -> None:
        if self._dir is not None and self._agent is not None and self._agent.poll() is None:
            subprocess.run([_tool("ssh-add"), "-D"], env=self.env(), capture_output=True)
        if self._agent is not None:
            self._agent.terminate()
            try:
                self._agent.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._agent.kill()
                self._agent.wait()
            self._agent = None
        if self._dir is not None:
            shutil.rmtree(self._dir, ignore_errors=True)
            self._dir = None
        self._glyph = b""

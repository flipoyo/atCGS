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


class AccessRefused(PermissionError):
    """The journals do not let this UID act as the requested layer."""


def challenge(nonce: bytes, uid: str, twin: str, when: int) -> bytes:
    return b"atCGS/session/v1\n" + canonical({"nonce": nonce.hex(), "uid": uid, "twin": twin, "time": when})


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
        grants = {repo: g for repo, g in state.roles(uid).items() if g.role == self.layer}
        if not grants:
            raise AccessRefused(f"this UID holds no {self.layer} grant")
        return grants

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

    # step 7
    def env(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        """The environment for a subprocess: the caller's, with this session's agent only."""
        if self._dir is None:
            raise ValueError("the session is closed")
        env = dict(os.environ if base is None else base)
        env.pop("SSH_AGENT_PID", None)
        env["SSH_AUTH_SOCK"] = str(self._dir / "agent")
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

"""@cgs: Pixi entry point and four-selector PRIME CGS OpFrontier adapter.

The system invariants, GitTree operations, memory, integrity and release
semantics remain exclusively in ComplexGitSync. `@cgs` only selects a System
Layer, resolves its own GitRepo frontiers and applies the PUBLIC boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Callable, Mapping, MutableMapping, Sequence

# Inner SemVer 2.0.0 of ComplexGraphSync/@cgs: the single source of truth that
# pixi.toml, spec/contracts.toml, candidate.json and the docs must match.
# The ALPHA stage is the `-alpha` prerelease; it is not the CGS-ALPHA engine pin.
__version__ = "1.1.0-alpha"
SYSTEM = f"ComplexGraphSync {__version__}"

# PRIME G is an ontology, not an alternate implementation of CGS invariants.
PRIME_G: tuple[str, ...] = ("NAME", "NODE", "EDGE", "OP*")

# The only executable @cgs selectors; exact and case-sensitive.
PRIME_CGS: tuple[str, ...] = ("OPX", "DEV", "USR", "PUB")

# (source_artifact, source_layer, destination_layer, destination_artifact).
# Four layers, three edges: PUB is terminal and no fourth edge exists.
TRANSITIONS: tuple[tuple[str, str, str, str], ...] = (
    (".gts", "OPX", "DEV", ".cgs"),
    (".cgs", "DEV", "USR", ".toml"),
    (".toml", "USR", "PUB", ".omniscience"),
)

# CGS-owned frontiers, not @cgitsync GitTree mounts; `*G` is kept literally.
FRONTIERS: tuple[tuple[str, tuple[str, str, str]], ...] = (
    (".poe", (".omniscience", ".cgs", "*G")),
    (".opx", (".cgitsync", ".omniscience", ".gts")),
)



def build_name(manifest: Path | None = None) -> str:
    """Build name from pixi.toml [tool.cgs]: build-name, else lower-case(project)."""
    with (manifest or ROOT / "pixi.toml").open("rb") as handle:
        meta = tomllib.load(handle).get("tool", {}).get("cgs", {})
    name = meta.get("build-name") or meta.get("project", "").lower()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", name):
        raise ValueError("pixi.toml [tool.cgs] needs a project or a build-name")
    return name


def commit_subject(summary: str) -> str:
    """Commit subject <build-name>-<version> <summary>, as in cgs-1.1.0-alpha."""
    return f"{build_name()}-{__version__} {summary}"


PUBLIC, PRIVATE = ".omniscience", ".cgitsync"
MOUNT_POLICY: Mapping[str, str] = {PUBLIC: "PUBLIC", PRIVATE: "PRIVATE"}
PRIVATE_LAYERS = frozenset({"OPX", "DEV"})

# Existing CGS-ALPHA verbs, reachable only behind an authorized OPX/DEV selector.
# `env show|check` is cgitsync's environment feature: @cgs and cgitsync share one
# Pixi environment, so its observation and drift check apply to both.
CORE_OPERATIONS = frozenset(
    {"bootstrap", "initialise", "status", "view-tree", "env", "--version", "--help", "-h"}
)
CORE_RELEASE = frozenset({("release", "freeze"), ("release", "list"), ("release", "load")})

# Operator configuration; never read from the request arguments.
AUTHORIZE_ENV = "ATCGS_AUTHORIZE"
MOUNTS_ENV = "ATCGS_MOUNTS"
# Set by `pixi run`; @cgs runs under this repository's Pixi environment only.
PIXI_ENV = "PIXI_PROJECT_ROOT"
ROOT = Path(__file__).resolve().parent

USAGE = """usage: @cgs {OPX,DEV,USR,PUB} [argument ...]
       @cgs --version       print the inner ComplexGraphSync SemVer

  OPX | DEV            emit the layer's outgoing OpFrontier transition
  OPX | DEV <op ...>   delegate an existing cgitsync operation (requires ATCGS_AUTHORIZE)
  USR                  emit the USR -> PUB transition
  PUB                  serve the read-only PUBLIC answer (.poe frontier)
  <layer> .omniscience resolve the PUBLIC mount
  OPX | DEV .cgitsync   resolve the PRIVATE mount (requires ATCGS_AUTHORIZE)
  OPX | DEV env show|check  observe or check the shared environment (requires ATCGS_AUTHORIZE)

Run it as: pixi run '@cgs' ..."""


class Evidence(str, Enum):
    """Distinct evidence states; only a real verifier may ever yield VERIFIED."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    UNAUTHORIZED = "unauthorized"
    NOT_REGISTERED = "not_registered"


class Unauthorized(PermissionError):
    """A selector or requester lacks the explicit grant for a PRIVATE frontier."""


@dataclass(frozen=True, slots=True)
class Transition:
    """Typed boundary descriptor; it never carries the artifact's contents."""

    source_artifact: str
    source_layer: str
    destination_layer: str
    destination_artifact: str
    evidence: Evidence = Evidence.UNVERIFIED

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (self.source_artifact, self.source_layer, self.destination_layer, self.destination_artifact)

    def as_dict(self) -> dict[str, object]:
        return {"transition": list(self.as_tuple()), "evidence": self.evidence.value}


@dataclass(frozen=True, slots=True)
class Request:
    layer: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpFrontier:
    """Minimal CGS -> CGS-ALPHA routing contract; never a second Op engine."""

    source: str = "CGS"
    target: str = "CGS-ALPHA"

    def serve_poex(self) -> tuple[str, str, str, str]:
        """Serve the exact POEX frontier descriptor; no execution or proof verdict."""
        return ("POEX", "NODE", "DELTA", "OPX")

    def emit(self, from_layer: str, to_layer: str) -> Transition:
        """Return the single approved edge; skips, reversals and new edges fail."""
        for edge in TRANSITIONS:
            if edge[1:3] == (from_layer, to_layer):
                return Transition(*edge)
        raise ValueError(f"no OpFrontier transition {from_layer!r} -> {to_layer!r}")

    def outgoing(self, layer: str) -> Transition | None:
        if layer not in PRIME_CGS:
            raise ValueError(f"unsupported @cgs selector: {layer!r}")
        return next((Transition(*edge) for edge in TRANSITIONS if edge[1] == layer), None)

    def accept(self, argv: Sequence[str]) -> Request:
        request = tuple(argv)
        if not request:
            raise ValueError("missing selector: OPX, DEV, USR, PUB")
        layer, args = request[0], request[1:]
        if layer not in PRIME_CGS:
            raise ValueError(f"unsupported @cgs selector: {layer!r} (expected OPX, DEV, USR or PUB)")
        if not args or (len(args) == 1 and args[0] in MOUNT_POLICY):
            return Request(layer, args)
        if layer in PRIVATE_LAYERS and (args[0] in CORE_OPERATIONS or args[:2] in CORE_RELEASE):
            return Request(layer, args)
        raise ValueError(f"unsupported @cgs {layer} argument: {args[0]!r}")


@dataclass(frozen=True, slots=True)
class Authorization:
    """Explicit owner grant, read from the operator environment only."""

    layers: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Authorization:
        raw = (os.environ if env is None else env).get(AUTHORIZE_ENV, "")
        granted = frozenset(part.strip() for part in raw.split(",") if part.strip())
        if not granted <= PRIVATE_LAYERS:
            raise ValueError(f"{AUTHORIZE_ENV} may only grant OPX and/or DEV")
        return cls(granted)

    def require(self, layer: str) -> None:
        if layer not in PRIVATE_LAYERS or layer not in self.layers:
            raise Unauthorized(f"{layer} requires explicit owner authorization ({AUTHORIZE_ENV})")


_COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_SEGMENT = re.compile(r"[A-Za-z0-9_.-]+")
_HOST = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_MOUNT_FIELDS = frozenset({"name", "repository", "ref", "commit", "policy", "writable", "provenance"})


def repository_identity(repository: str) -> str | None:
    """Canonical `host/owner/name` identity, or None for local paths and traversal."""
    if repository.startswith("github:"):
        host, path = "github.com", repository[len("github:"):]
    elif repository.startswith("https://"):
        host, _, path = repository[len("https://"):].partition("/")
        if not _HOST.fullmatch(host):
            return None
    else:
        return None
    segments = path.removesuffix(".git").split("/")
    if len(segments) != 2 or any(s in {".", ".."} or not _SEGMENT.fullmatch(s) for s in segments):
        return None
    return "/".join([host.lower(), *(s.lower() for s in segments)])


@dataclass(frozen=True, slots=True)
class CgsMount:
    """A @cgs GitRepo frontier, unrelated to @cgitsync GitTree/Memory mounts."""

    name: str
    repository: str
    ref: str
    commit: str
    policy: str
    writable: bool = False
    provenance: str = ""

    def __post_init__(self) -> None:
        # Messages name the mount, never the (possibly PRIVATE) repository.
        if MOUNT_POLICY.get(self.name) != self.policy:
            raise ValueError(f"mount {self.name!r} is not bound to its frozen policy")
        if self.policy == "PUBLIC" and self.writable is not False:
            raise ValueError(f"mount {self.name!r} is PUBLIC and must be read-only")
        if not isinstance(self.writable, bool):
            raise ValueError(f"mount {self.name!r}: writable must be a boolean")
        if repository_identity(self.repository) is None:
            raise ValueError(f"mount {self.name!r}: invalid repository identity")
        if not self.ref or ".." in self.ref or self.ref.startswith(("-", "/")):
            raise ValueError(f"mount {self.name!r}: invalid ref")
        if not _COMMIT.fullmatch(self.commit):
            raise ValueError(f"mount {self.name!r}: ref must be pinned to a full commit id")

    @property
    def identity(self) -> str:
        return repository_identity(self.repository)  # type: ignore[return-value]

    def public_view(self) -> dict[str, str]:
        """Allowlisted fields only; no evidence is claimed without a verifier."""
        return {"repository": self.repository, "commit": self.commit, "evidence": Evidence.UNVERIFIED.value}

    def private_view(self) -> dict[str, object]:
        return {
            "name": self.name, "repository": self.repository, "ref": self.ref, "commit": self.commit,
            "policy": self.policy, "writable": self.writable, "evidence": Evidence.UNVERIFIED.value,
        }


@dataclass(frozen=True, slots=True)
class MountTable:
    mounts: tuple[CgsMount, ...] = ()

    def __post_init__(self) -> None:
        names = [mount.name for mount in self.mounts]
        if len(set(names)) != len(names):
            raise ValueError("duplicate @cgs mount name")
        if len({mount.identity for mount in self.mounts}) != len(self.mounts):
            raise ValueError("one GitRepo cannot back both PUBLIC and PRIVATE mounts")

    @classmethod
    def load(cls, path: Path) -> MountTable:
        with path.open("rb") as handle:
            entries = tomllib.load(handle).get("mount", [])
        mounts = []
        for entry in entries:
            if not isinstance(entry, dict) or not set(entry) <= _MOUNT_FIELDS:
                raise ValueError("unknown @cgs mount field")
            try:
                mounts.append(CgsMount(**entry))
            except TypeError:
                raise ValueError("incomplete @cgs mount entry") from None
        return cls(tuple(mounts))

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> MountTable:
        path = (os.environ if env is None else env).get(MOUNTS_ENV)
        return cls.load(Path(path)) if path else cls()

    def public(self) -> CgsMount | None:
        return next((mount for mount in self.mounts if mount.policy == "PUBLIC"), None)

    def resolve(self, name: str, layer: str, authorization: Authorization) -> CgsMount | None:
        """Resolve one frontier; PRIVATE needs an authorized OPX/DEV, no fallback."""
        if name not in MOUNT_POLICY:
            raise ValueError(f"unknown @cgs mount: {name!r}")
        if MOUNT_POLICY[name] == "PRIVATE":
            if layer not in PRIVATE_LAYERS:
                raise Unauthorized(f"{layer} cannot access PRIVATE {name}")
            authorization.require(layer)
        return next((mount for mount in self.mounts if mount.name == name), None)


def public_answer(table: MountTable) -> dict[str, object]:
    """PUB: read-only PUBLIC view; never touches PRIVATE mounts or the core."""
    mount = table.public()
    return {
        "layer": "PUB",
        "frontier": {".poe": list(dict(FRONTIERS)[".poe"])},
        "requestable": "*G",
        PUBLIC: mount.public_view() if mount else {"evidence": Evidence.UNAVAILABLE.value},
    }


MICROCODE = ROOT / "microcode"
GLYPH_BYTES = 256 * 256 // 8  # a GLYPH is 256x256 bits
_COMPARED = re.compile(
    r"POEX COMPARED: 64 packets x 4x256 bits; quartets=16384; zeros=(\d+); equal=(yes|no); evidence=UNVERIFIED"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(name: str, directory: Path, compiler: str = "cc") -> Path:
    """Compile microcode/<name>.c with the flags of microcode/README.md."""
    binary = directory / name
    subprocess.run(
        [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-o", str(binary), str(MICROCODE / f"{name}.c")],
        check=True,
    )
    return binary


@dataclass(frozen=True, slots=True)
class PoeVector:
    """.poe: one 4x256-bit POEX packet, one sha256 credential per PRIME CGS layer."""

    opx: str  # sha256(GLYPH); OPX only
    dev: str  # sha256(temporary DEV ssh public key)
    usr: str  # sha256(NAME)
    pub: str  # sha256(SEED), the unique ID of NAME

    def slot(self, layer: str) -> str:
        """The one component a layer receives."""
        if layer not in PRIME_CGS:
            raise ValueError(f"unsupported PRIME CGS layer: {layer!r}")
        return getattr(self, layer.lower())

    def packet(self) -> bytes:
        """4 x 256 bits = 128 bytes, in PRIME CGS order."""
        return b"".join(bytes.fromhex(self.slot(layer)) for layer in PRIME_CGS)


@dataclass(frozen=True, slots=True)
class EOPX:
    """Existence of Proof: wraps the C eopx microcode, the birth protocol.

    `opx` maps NAME -> (hash(SEED), hash(GLYPH)), known by OPX only. A GLYPH
    lives in this process only while it is hashed or compared; nobody stores it.
    """

    binary: Path
    opx: MutableMapping[str, tuple[str, str]]

    def glyph(self, seed: bytes) -> bytes:
        """Rebuild the GLYPH of a SEED; the microcode refuses a non-square or small SEED."""
        result = subprocess.run([str(self.binary)], input=seed, capture_output=True)
        if result.returncode != 0 or len(result.stdout) != GLYPH_BYTES:
            raise ValueError(f"eopx microcode refused the SEED: {result.stderr.decode().strip()}")
        return result.stdout

    def birth(self, name: str, seed: bytes) -> None:
        """Register a new NAME: hash(SEED) is its unique ID, hash(GLYPH) goes to OPX."""
        if name in self.opx:
            raise ValueError(f"{name!r} already exists in PoE")
        seed_id = sha256(seed)
        if any(registered == seed_id for registered, _ in self.opx.values()):
            raise ValueError("hash(SEED) is already the ID of another NAME")
        self.opx[name] = (seed_id, sha256(self.glyph(seed)))


@dataclass(frozen=True, slots=True)
class POEX:
    """Proof of Existence: the wallet, wrapping the C poex microcode.

    The microcode's only purpose is comparison. POEX rebuilds both GLYPHs with
    EOPX and hands them to poex; neither leaves the process.
    """

    binary: Path
    eopx: EOPX

    def exists(self, name: str) -> bool:
        """Does NAME exist in PoE? The only question POEX asks."""
        return name in self.eopx.opx

    def compare(self, seed_a: bytes, seed_b: bytes) -> bool:
        """Rebuild two unknown GLYPHs, then let poex compare them: equal iff zeros = 65536."""
        glyphs = self.eopx.glyph(seed_a) + self.eopx.glyph(seed_b)
        result = subprocess.run([str(self.binary), "--packet"], input=glyphs, capture_output=True)
        compared = _COMPARED.search(result.stdout.decode())
        if result.returncode not in (0, 1) or compared is None:
            raise ValueError(f"poex microcode refused the GLYPHs: {result.stderr.decode().strip()}")
        return compared.group(2) == "yes"

    def poe(
        self, name: str, ask_seed: Callable[[], bytes], send: Callable[[Path, str], None]
    ) -> PoeVector:
        """Deliver .poe for NAME; a NAME not in PoE is born through EOPX first.

        Once NAME exists in PoE, `send` is the OpFrontier request
        ComplexGraphSync -> ComplexGitSync: it receives the temporary DEV private
        key path, valid only during the call, and hash(SEED), never the GLYPH.
        The key set is destroyed when `send` returns.
        """
        if not self.exists(name):
            self.eopx.birth(name, ask_seed())
        seed_id, glyph_id = self.eopx.opx[name]
        with tempfile.TemporaryDirectory(prefix="poex-") as tmp:
            private = Path(tmp) / "id_ed25519"
            # The ssh-keygen core of github.com/flipoyo/sshKeyGen, without ~/.ssh or ssh-agent.
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"poex-{seed_id}", "-f", str(private)],
                check=True, capture_output=True,
            )
            public = Path(f"{private}.pub").read_bytes().strip()
            send(private, seed_id)
        return PoeVector(glyph_id, sha256(public), sha256(name.encode()), seed_id)


def cgs(handler: Callable[[Request], int]) -> Callable[[Sequence[str] | None], int]:
    """Decorator for the entry point: accept one PRIME CGS selector, then delegate."""

    @wraps(handler)
    def entry(argv: Sequence[str] | None = None) -> int:
        raw = tuple(sys.argv[1:] if argv is None else argv)
        if raw in {("--help",), ("-h",)}:
            print(USAGE)
            return 0
        if raw == ("--version",):
            print(SYSTEM)
            return 0
        return handler(OpFrontier().accept(raw))

    return entry


def _emit(payload: Mapping[str, object]) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


@cgs
def main(request: Request) -> int:
    table, authorization = MountTable.from_env(), Authorization.from_env()
    if request.args and request.args[0] in MOUNT_POLICY:
        name = request.args[0]
        mount = table.resolve(name, request.layer, authorization)
        if mount is None:
            return _emit({"mount": name, "evidence": Evidence.UNAVAILABLE.value})
        return _emit({"mount": name, **(mount.private_view() if mount.policy == "PRIVATE" else mount.public_view())})
    if not request.args:
        if request.layer == "PUB":
            return _emit(public_answer(table))
        return _emit({"layer": request.layer, **OpFrontier().outgoing(request.layer).as_dict()})
    authorization.require(request.layer)
    # ComplexGitSync.cli.main already routes writes via RoutedClient -> Op.
    from ComplexGitSync.cli import main as cgitsync_main

    return cgitsync_main(request.args)


def require_pixi(env: Mapping[str, str] | None = None) -> None:
    """Refuse to run outside this repository's Pixi environment."""
    root = (os.environ if env is None else env).get(PIXI_ENV, "")
    if not root or Path(root).resolve() != ROOT:
        raise ValueError(f"run under Pixi only: pixi run <task> from {ROOT.name}")


def run(argv: Sequence[str] | None = None) -> int:
    try:
        require_pixi()
        return main(argv)
    except Unauthorized as exc:
        print(f"@cgs: {exc}", file=sys.stderr)
        return 3
    except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"@cgs: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())

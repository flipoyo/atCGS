"""@cgs: Pixi entry point and four-selector PRIME CGS OpFrontier adapter.

The system invariants, GitTree operations, memory, integrity and release
semantics remain exclusively in ComplexGitSync. `@cgs` only selects a System
Layer, resolves its own GitRepo frontiers and applies the PUBLIC boundary.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ComplexGitSync.orchestre.op_levels import LEVELS

# Inner SemVer 2.0.0 of ComplexGraphSync/@cgs: the single source of truth that
# pixi.toml, spec/contracts.toml and the docs must match.
# The ALPHA stage is the `-alpha` prerelease; it is not the CGS-ALPHA engine pin.
__version__ = "1.10.0-alpha"
SYSTEM = f"ComplexGraphSync {__version__}"

# PRIME G is an ontology, not an alternate implementation of CGS invariants.
PRIME_G: tuple[str, ...] = ("NAME", "NODE", "EDGE", "OP*")

# The four levels are ComplexGitSync's (LinkAtCGS, op_levels), not atCGS's: one definition,
# used by both sides of the OpFrontier on CGS-ALPHA. The only executable @cgs selectors.
PRIME_CGS: tuple[str, ...] = tuple(LEVELS)

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
    """Commit subject <build-name>-<version> <summary>, as in cgs-1.7.1-alpha."""
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
IDENTITY_VERBS = frozenset({"init", "request", "enrol", "admit", "revoke", "login", "publish", "intake", "onboard"})
# The cgitsync commands `<LAYER> login TWIN <op ...>` may run, by level: the everyday
# loop, so atCGS is developed through @cgs (Dogfooding). The keys a level gets decide
# what the remote accepts; this list only keeps a level to the commands it needs.
_USR_OPS = frozenset({"status", "view-tree", "fetch", "pull", "validate"})
_DEV_OPS = _USR_OPS | {"add", "rm", "commit", "push", "branch", "checkout", "merge", "autofix"}
_OPX_OPS = _DEV_OPS | {"tag", "release", "bootstrap", "initialise", "omniscience", "memory", "promote",
                       "env", "verify", "unlock", "self-history"}
LOGIN_OPS: Mapping[str, frozenset[str]] = {"USR": _USR_OPS, "DEV": _DEV_OPS, "OPX": _OPX_OPS}

# Operator configuration; never read from the request arguments.
AUTHORIZE_ENV = "ATCGS_AUTHORIZE"
MOUNTS_ENV = "ATCGS_MOUNTS"
REGISTER_ENV = "ATCGS_REGISTER"  # overrides REGISTER, the journals' directory
# atCGS's register (identity.jsonl, access.jsonl) lives in the project's memory,
# .cgitsync/.memory/.register: private, per project. Its identity part and chain
# heads may be projected to .omniscience, which holds no names.
# Set by `pixi run`; @cgs runs under this repository's Pixi environment only.
PIXI_ENV = "PIXI_PROJECT_ROOT"
ROOT = Path(__file__).resolve().parents[1]

USAGE = """usage: @cgs {OPX,DEV,USR,PUB} [argument ...]
       @cgs --version       print the inner ComplexGraphSync SemVer

  OPX | DEV            emit the layer's outgoing OpFrontier transition
  OPX | DEV <op ...>   delegate an existing cgitsync operation (requires ATCGS_AUTHORIZE)
  USR                  emit the USR -> PUB transition
  PUB                  serve the read-only PUBLIC answer (.poe frontier)
  <layer> .omniscience resolve the PUBLIC mount
  OPX | DEV .cgitsync   resolve the PRIVATE mount (requires ATCGS_AUTHORIZE)
  OPX | DEV env show|check  observe or check the shared environment (requires ATCGS_AUTHORIZE)

  Identity and access (ATCGS_REGISTER; logins and passwords are asked, never passed):
  OPX init                     enrol OPX itself, with the key pinned in spec/contracts.toml
  <layer> request OUT REPO ROLE [REPO ROLE ...]
                               new ssh keys, sealed in your GLYPH; OUT is the request for OPX
  <layer> request --register PROJECT=ROLE [--register ...] [--name NAME] OUT.toml
                               the same for whole projects; OUT.toml is the registration file for the Owner
  OPX intake [FOLDER]          build the day's list from the registration files (no password)
  OPX onboard LIST [--plan]    enrol, publish, admit, install deploy keys, push the registers: one run
  OPX enrol REQUEST            enrol the requester only (master register); no grant
  OPX admit REQUEST            enrol the requester and grant what it asks
  OPX revoke UID [REPO]        revoke a UID, or only its grant on REPO
  OPX publish                  copy the identity journal to .omniscience (branch CGS-MOLO); projects copy it
  OPX | DEV | USR login TWIN [op ...]
                               open a session: load the granted ssh keys into a private
                               ssh-agent and run `cgitsync op ...` through it, each repo
                               reached with its own key only. USR: status, fetch, pull;
                               DEV: + add, commit, push, branch, checkout, merge;
                               OPX: + tag, release, bootstrap, initialise, memory ...
                               OPX promote DIR FROM TO: fast-forward branch TO of the repo at
                               DIR (in this tree) to FROM, pushed with that repo's key only.
                               TWIN.cgs is written only by a bare login, where it was typed.

Run it as: pixi run cgs ..."""


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
        if _identity_request(layer, args):
            return Request(layer, args)
        if args[0] == "login" and layer in LOGIN_OPS and len(args) >= 3:
            raise ValueError(f"{layer} may not run {args[2]!r} through login; {layer} runs: "
                             f"{', '.join(sorted(LOGIN_OPS[layer]))}")
        if args[0] == "request":
            raise ValueError(f"{layer} request needs OUT then at least one REPOSITORY ROLE pair: "
                             f"{layer} request OUT github:owner/repo DEV [REPO ROLE ...], "
                             f"or {layer} request --register PROJECT=ROLE [--name NAME] OUT.toml")
        raise ValueError(f"unsupported @cgs {layer} argument: {args[0]!r}")


def _identity_request(layer: str, args: Sequence[str]) -> bool:
    """The identity verbs and their arity (REFERENCE.md § 6); the arguments are never secrets."""
    verb, rest = args[0], args[1:]
    if verb == "init":
        return layer == "OPX" and not rest
    if verb == "request":
        if rest and rest[0] in ("--register", "--name"):  # request --register P=R [--name N] OUT.toml
            return len(rest) >= 3 and "--register" in rest
        return len(rest) >= 3 and len(rest) % 2 == 1
    if verb == "intake":
        return layer == "OPX" and len(rest) <= 1
    if verb == "onboard":  # LIST [--plan]: exactly one path, at most one --plan
        paths = [a for a in rest if not a.startswith("--")]
        return layer == "OPX" and len(paths) == 1 and all(a == "--plan" for a in rest if a.startswith("--")) \
            and rest.count("--plan") <= 1
    if verb == "admit":
        return layer == "OPX" and len(rest) == 1
    if verb == "enrol":
        return layer == "OPX" and len(rest) == 1
    if verb == "revoke":
        return layer == "OPX" and len(rest) in (1, 2)
    if verb == "publish":
        return layer == "OPX" and not rest
    if verb == "login":
        return layer in LOGIN_OPS and len(rest) >= 1 and (len(rest) == 1 or rest[1] in LOGIN_OPS[layer])
    return False


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


def public_answer(table: MountTable) -> dict[str, object]:
    """PUB: read-only PUBLIC view; never touches PRIVATE mounts or the core."""
    mount = table.public()
    return {
        "layer": "PUB",
        "frontier": {".poe": list(dict(FRONTIERS)[".poe"])},
        "requestable": "*G",
        PUBLIC: mount.public_view() if mount else {"evidence": Evidence.UNAVAILABLE.value},
    }


@cgs
def main(request: Request) -> int:
    table, authorization = MountTable.from_env(), Authorization.from_env()
    if request.args and request.args[0] in IDENTITY_VERBS:
        from atcgs.commands import dispatch  # the identity layer: REFERENCE.md § 6

        return _emit(dispatch(request, authorization))
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


# The two manifests of this repository: atCGS as installed (pinned ComplexGitSync), and
# @cgs, the development Operating Space with ./ComplexGitSync live.
MANIFEST_ROOTS = (ROOT, ROOT / "@cgs")


def require_pixi(env: Mapping[str, str] | None = None) -> None:
    """Refuse to run outside this repository's Pixi environments (root, or @cgs)."""
    root = (os.environ if env is None else env).get(PIXI_ENV, "")
    if not root or Path(root).resolve() not in MANIFEST_ROOTS:
        raise ValueError(f"run under Pixi only: pixi run cgs ... from {ROOT.name}")


def run(argv: Sequence[str] | None = None) -> int:
    try:
        require_pixi()
        return main(argv)
    except PermissionError as exc:  # Unauthorized, AccessRefused
        print(f"@cgs: {exc}", file=sys.stderr)
        return 3
    except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"@cgs: {exc}", file=sys.stderr)
        return 2


"""@cgs: Pixi entry point and strict ALPHA OpFrontier adapter.

The system invariants, GitTree operations, memory, integrity and release
semantics remain exclusively in ComplexGitSync.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Sequence


# PRIME G is an ontology, not an alternate implementation of CGS invariants.
PRIME_G: tuple[str, ...] = ("NAME", "NODE", "EDGE", "OP*")


@dataclass(frozen=True, slots=True)
class OpFrontier:
    """Minimal CGS -> CGS-ALPHA routing contract; never a second Op engine."""

    source: str = "CGS"
    target: str = "CGS-ALPHA"

    def serve_poex(self) -> tuple[str, str, str, str]:
        """Serve the exact POEX frontier descriptor; no execution or proof verdict."""
        return ("POEX", "NODE", "DELTA", "OPX")

    def accept(self, argv: Sequence[str]) -> tuple[str, ...]:
        request = tuple(argv)
        if not request:
            raise ValueError("missing operation: bootstrap, initialise, status, view-tree, release")
        if request[0] in {"--help", "-h", "--version"}:
            return request
        if request[0] in {"bootstrap", "initialise", "status", "view-tree"}:
            return request
        if len(request) >= 2 and request[:2] in {
            ("release", "freeze"),
            ("release", "list"),
            ("release", "load"),
        }:
            return request
        raise ValueError(f"unsupported @cgs ALPHA operation: {request[0]}")


def cgs(handler: Callable[[Sequence[str]], int]) -> Callable[[Sequence[str] | None], int]:
    """Decorator for the ALPHA entry point: validate, then delegate unchanged."""

    @wraps(handler)
    def entry(argv: Sequence[str] | None = None) -> int:
        request = OpFrontier().accept(sys.argv[1:] if argv is None else argv)
        return handler(request)

    return entry


@cgs
def main(argv: Sequence[str]) -> int:
    # ComplexGitSync.cli.main already routes writes via RoutedClient -> Op.
    from ComplexGitSync.cli import main as cgitsync_main

    return cgitsync_main(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"@cgs: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

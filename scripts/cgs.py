#!/usr/bin/env python3
"""`pixi run cgs ...`: the one command, whichever ComplexGitSync this checkout should run.

    pixi run cgs OPX login ComplexGraphSync status

Where the development Operating Space is declared, that is `@cgs/pixi.toml` next to
an `./ComplexGitSync` checkout, the root task hands over to it, so the live checkout
runs. Anywhere else (a plain clone, a project's read-only gate `.atcgs`) atCGS runs
here, on the pinned ComplexGitSync. `ATCGS_PINNED=1` keeps the pinned one even where
the checkout exists. Inside `@cgs/pixi.toml` the `cgs` task runs atCGS directly.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "@cgs"


def handover(argv: Sequence[str], env: Mapping[str, str], root: Path = ROOT) -> list[str] | None:
    """The `pixi run -m @cgs cgs ...` to exec instead, or None to run atCGS here."""
    dev = root / "@cgs"
    if env.get("ATCGS_PINNED") or not (dev / "pixi.toml").is_file():
        return None
    if not (root / "ComplexGitSync" / "pyproject.toml").is_file():
        return None
    if Path(env.get("PIXI_PROJECT_ROOT", "")).resolve() == dev.resolve():
        return None  # already in the development manifest
    return ["pixi", "run", "-m", str(dev), "cgs", *argv]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = handover(args, os.environ)
    if command is not None:
        pixi = shutil.which("pixi")
        if pixi is None:
            print("cgs: pixi is not on PATH; run `pixi run -m @cgs cgs ...`, or set ATCGS_PINNED=1", file=sys.stderr)
            return 2
        os.execv(pixi, [pixi, *command[1:]])
    sys.path.insert(0, str(ROOT))
    from atcgs import run

    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

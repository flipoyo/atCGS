#!/usr/bin/env python3
"""Bump atCGS's inner SemVer: every mention of it, or none.

    pixi run bump-version patch              # 1.13.0-alpha -> 1.13.1-alpha
    pixi run bump-version minor              # 1.13.0-alpha -> 1.14.0-alpha
    pixi run bump-version minor --pre beta   # 1.13.0-alpha -> 1.14.0-beta
    pixi run bump-version --release          # 1.13.0-alpha -> 1.13.0
    pixi run bump-version patch --dry-run    # prints the change, writes nothing

Adapted from ComplexGitSync's bump_version.py (its .dev mount). Two differences: the
stage of atCGS is a bare `-alpha`, with no counter, and a level keeps it (the whole
alpha series is `X.Y.Z-alpha` on CGS-ALPHA), where ComplexGitSync drops it; and the
targets are atCGS's own, the ones tests/test_version.py checks. `atcgs.__version__` is
the single source; the others follow it. Commit subjects are then
`<build-name>-<version> ...` (atcgs.commit_subject).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_PATH = ROOT / "atcgs" / "__init__.py"
_V = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
_INIT_RE = re.compile(rf'(^__version__ = ")({_V})(")', re.MULTILINE)


class VersionSyncError(RuntimeError):
    """A version that is not SemVer, or a mention that cannot be found or written."""


@dataclass(frozen=True)
class Target:
    """One file, and the patterns that must each match once: (prefix)(version)(suffix)."""

    path: str
    patterns: tuple[str, ...]


TARGETS = (
    Target("atcgs/__init__.py", (_INIT_RE.pattern,)),
    Target("pixi.toml", (rf'(^version = ")({_V})(")',)),
    Target("@cgs/pixi.toml", (rf'(^version = ")({_V})(")',)),
    Target("spec/contracts.toml", (rf"(^# atCGS )({_V})( )", rf'(^version = ")({_V})(")')),
    Target("README.md", (rf"(^# atCGS — ComplexGraphSync )({_V})($)",)),
    Target("ALPHA.md", (rf"(^Inner version: `)({_V})(`)", rf"(# ComplexGraphSync )({_V})( \(local)")),
    Target("TUTOS/TUTO_1_OPERATE_A_PROJECT.md", (rf"(^\*\*atCGS )({_V})(,)",)),
    Target("TUTOS/TUTO_2_OMNISCIENCE.md", (rf"(^\*\*atCGS )({_V})(,)",)),
)


def parse_version(text: str) -> tuple[int, int, int, str | None]:
    match = SEMVER.match(text)
    if match is None:
        raise VersionSyncError(f"{text!r} is not a valid SemVer 2.0.0 version")
    return int(match[1]), int(match[2]), int(match[3]), match[4]


def read_current_version(init_path: Path = INIT_PATH) -> str:
    match = _INIT_RE.search(init_path.read_text(encoding="utf-8"))
    if match is None:
        raise VersionSyncError(f"{init_path}: no __version__ field found")
    parse_version(match[2])
    return match[2]


def next_version(current: str, level: str | None = None, pre: str | None = None, release: bool = False) -> str:
    """The next version: a *level* keeps the stage unless *pre* names another; *release* drops it."""
    major, minor, patch, stage = parse_version(current)
    if release:
        if level or pre or stage is None:
            raise VersionSyncError(f"{current} is not a pre-release" if stage is None else "--release takes no level")
        return f"{major}.{minor}.{patch}"
    if level is None:
        raise VersionSyncError("Specify a bump level (major, minor, patch) or --release")
    major, minor, patch = {"major": (major + 1, 0, 0), "minor": (major, minor + 1, 0),
                           "patch": (major, minor, patch + 1)}[level]
    stage = pre or stage
    return f"{major}.{minor}.{patch}" + (f"-{stage}" if stage else "")


def apply_version(new: str, root: Path = ROOT, targets: tuple[Target, ...] = TARGETS) -> list[str]:
    """Rewrite every target; check them all first, so a bump is all the files or none of them."""
    parse_version(new)
    texts: dict[Path, str] = {}
    for target in targets:
        path = root / target.path
        if not path.is_file():
            raise VersionSyncError(f"{target.path}: missing; nothing was written")
        text = path.read_text(encoding="utf-8")
        for pattern in target.patterns:
            text, count = re.subn(pattern, rf"\g<1>{new}\g<3>", text, count=1, flags=re.MULTILINE)
            if count != 1:
                raise VersionSyncError(f"{target.path}: could not find a version field ({pattern}); nothing was written")
        texts[path] = text
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8")
    return [target.path for target in targets]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bump atCGS's inner SemVer in every file that states it.")
    parser.add_argument("level", nargs="?", choices=("major", "minor", "patch"))
    parser.add_argument("--pre", metavar="STAGE", help="the pre-release stage of the new version (default: the current one)")
    parser.add_argument("--release", action="store_true", help="drop the pre-release stage")
    parser.add_argument("--dry-run", action="store_true", help="print the change, write nothing")
    args = parser.parse_args(argv)
    if args.level is None and not args.release:
        parser.error("a level (major, minor, patch) or --release is required")
    try:
        current = read_current_version()
        new = next_version(current, args.level, args.pre, args.release)
        written = [] if args.dry_run else apply_version(new)
    except VersionSyncError as exc:
        print(f"bump-version: {exc}", file=sys.stderr)
        return 2
    print(f"{current} -> {new}" + (" (dry run)" if args.dry_run else ""))
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

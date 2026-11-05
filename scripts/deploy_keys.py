#!/usr/bin/env python3
"""Dogfooding S2: print the GitHub commands that install the access journal's keys.

    pixi run deploy-keys                  # reads .cgitsync/.memory/.register (ATCGS_REGISTER overrides it)
    pixi run deploy-keys --repo github:flipoyo/MOLONARI1D   # only the named repos (the others are installed)

One deploy key per active grant on a github: repo, write access for OPX and DEV,
read-only for USR. It prints `gh api` commands and runs nothing: the owner reads
them and runs them. Revoked grants are not listed; remove their keys by hand
(GitHub repo settings, Deploy keys) until M7 (short ticket github-deploy-keys).
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atcgs import require_pixi  # noqa: E402
from atcgs.commands import register  # noqa: E402
from atcgs.journal import State  # noqa: E402
from atcgs.session import repo_path  # noqa: E402


def commands(state: State, only: frozenset[str] = frozenset()) -> list[str]:
    """One `gh api` per active grant; with *only*, just the grants on those repos (owner/name or github:o/n)."""
    wanted = {repo_path(repo) for repo in only}
    lines = []
    for uid in sorted(state.active):
        for repo, grant in sorted(state.roles(uid).items()):
            if not repo.startswith("github:") or (wanted and repo_path(repo) not in wanted):
                continue
            read_only = "false" if grant.role in ("OPX", "DEV") else "true"
            title = f"atCGS {grant.role} {uid[:12]}"
            lines.append(" ".join([
                "gh api", shlex.quote(f"repos/{repo_path(repo)}/keys"), "-f", shlex.quote(f"title={title}"),
                "-f", shlex.quote(f"key={grant.ssh}"), "-F", f"read_only={read_only}",
            ]))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="print the gh commands that install the access journal's deploy keys")
    parser.add_argument("--repo", action="append", default=[], metavar="REPO",
                        help="only the grants on this repo (github:owner/name); repeatable. Default: all")
    args = parser.parse_args(argv)
    require_pixi()
    lines = commands(register().state(), frozenset(args.repo))
    print(f"# {len(lines)} deploy key(s) from the access journal; review, then run:")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

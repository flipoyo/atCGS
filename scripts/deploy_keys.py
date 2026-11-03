#!/usr/bin/env python3
"""Dogfooding S2: print the GitHub commands that install the access journal's keys.

    pixi run deploy-keys        # reads .cgitsync/.memory/.register (ATCGS_REGISTER overrides it)

One deploy key per active grant on a github: repo, write access for OPX and DEV,
read-only for USR. It prints `gh api` commands and runs nothing: the owner reads
them and runs them. Revoked grants are not listed; remove their keys by hand
(GitHub repo settings, Deploy keys) until M7 (short ticket github-deploy-keys).
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atcgs import require_pixi  # noqa: E402
from atcgs.commands import register  # noqa: E402
from atcgs.journal import State  # noqa: E402
from atcgs.session import repo_path  # noqa: E402


def commands(state: State) -> list[str]:
    lines = []
    for uid in sorted(state.active):
        for repo, grant in sorted(state.roles(uid).items()):
            if not repo.startswith("github:"):
                continue
            read_only = "false" if grant.role in ("OPX", "DEV") else "true"
            title = f"atCGS {grant.role} {uid[:12]}"
            lines.append(" ".join([
                "gh api", shlex.quote(f"repos/{repo_path(repo)}/keys"), "-f", shlex.quote(f"title={title}"),
                "-f", shlex.quote(f"key={grant.ssh}"), "-F", f"read_only={read_only}",
            ]))
    return lines


def main() -> int:
    require_pixi()
    lines = commands(register().state())
    print(f"# {len(lines)} deploy key(s) from the access journal; review, then run:")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

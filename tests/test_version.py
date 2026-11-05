"""Inner SemVer drift regressions: every version mention must match atcgs.__version__."""

import io
import re
import subprocess
import sys
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from atcgs import SYSTEM, __version__, run

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from contract_check import inspect  # noqa: E402

# Official SemVer 2.0.0 regex (https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string).
SEMVER = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
STALE = re.compile(r"\b0\.0\.0\b")


def toml(path: str) -> dict:
    with (ROOT / path).open("rb") as handle:
        return tomllib.load(handle)


class VersionTests(unittest.TestCase):
    def test_semver_2_0_0_alpha_prerelease(self):
        match = SEMVER.fullmatch(__version__)
        self.assertIsNotNone(match, __version__)
        self.assertEqual(match["prerelease"].split(".")[0], "alpha")
        for bad in ("ALPHA 0.0.0", "0.1", "01.0.0", "0.1.0-", "0.1.0-alpha..1", "v0.1.0"):
            with self.subTest(bad=bad):
                self.assertIsNone(SEMVER.fullmatch(bad))

    def test_manifests_match(self):
        self.assertEqual(toml("pixi.toml")["workspace"]["version"], __version__)
        self.assertEqual(toml("@cgs/pixi.toml")["workspace"]["version"], __version__)
        self.assertEqual(toml("spec/contracts.toml")["contract"]["version"], __version__)
        self.assertEqual(inspect()["version"], __version__)

    def test_docs_match(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(readme[0], f"# atCGS — {SYSTEM}")
        self.assertIn(f"`{__version__}`", (ROOT / "ALPHA.md").read_text(encoding="utf-8"))

    def test_no_stale_version_literal(self):
        # atCGS's own tracked files only: the nested repositories (ComplexGitSync, the
        # .agent mounts) carry their own versions, and some links point into absent mounts.
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
        for path in sorted(ROOT / name for name in tracked.stdout.decode().split("\0") if name):
            if path.suffix not in {".py", ".md", ".toml", ".json", ".c", ".cgs"} or path.name == Path(__file__).name \
                    or not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(path=str(path.relative_to(ROOT)), line=number):
                    self.assertIsNone(STALE.search(line), line)

    def test_cli_version_is_local(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = run(["--version"])
        self.assertEqual((code, out.getvalue().strip()), (0, SYSTEM))


if __name__ == "__main__":
    unittest.main()

"""scripts/bump_version.py: the next SemVer, and every mention of it rewritten, or none."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from atcgs import __version__

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bump_version  # noqa: E402


class NextVersionTests(unittest.TestCase):
    def test_a_level_keeps_the_alpha_stage(self):
        for current, level, expected in (("1.13.0-alpha", "patch", "1.13.1-alpha"),
                                         ("1.13.4-alpha", "minor", "1.14.0-alpha"),
                                         ("1.13.4-alpha", "major", "2.0.0-alpha"),
                                         ("1.9.9", "patch", "1.9.10")):
            with self.subTest(current=current, level=level):
                self.assertEqual(bump_version.next_version(current, level), expected)

    def test_pre_changes_the_stage_and_release_drops_it(self):
        self.assertEqual(bump_version.next_version("1.13.0-alpha", "minor", pre="beta"), "1.14.0-beta")
        self.assertEqual(bump_version.next_version("1.13.0-alpha", release=True), "1.13.0")
        with self.assertRaisesRegex(bump_version.VersionSyncError, "not a pre-release"):
            bump_version.next_version("1.13.0", release=True)

    def test_a_level_is_required_and_the_version_is_semver(self):
        with self.assertRaisesRegex(bump_version.VersionSyncError, "Specify a bump level"):
            bump_version.next_version("1.13.0-alpha")
        for bad in ("0002.88", "1.13", "v1.13.0"):
            with self.subTest(bad=bad), self.assertRaisesRegex(bump_version.VersionSyncError, "not a valid SemVer"):
                bump_version.next_version(bad, "patch")


class ApplyVersionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="cgs-bump-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for target in bump_version.TARGETS:
            (self.root / target.path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / target.path, self.root / target.path)

    def test_the_real_files_all_have_their_version_field(self):
        written = bump_version.apply_version("9.8.7-alpha", root=self.root)
        self.assertEqual(len(written), len(bump_version.TARGETS))
        for target in bump_version.TARGETS:
            text = (self.root / target.path).read_text(encoding="utf-8")
            with self.subTest(path=target.path):
                self.assertEqual(text.count("9.8.7-alpha"), len(target.patterns))
                self.assertNotIn(__version__, text.replace("before 1.13.0", ""))

    def test_nothing_is_written_when_one_target_has_no_field(self):
        readme = self.root / "README.md"
        readme.write_text("# atCGS\n", encoding="utf-8")
        with self.assertRaisesRegex(bump_version.VersionSyncError, "README.md: could not find"):
            bump_version.apply_version("9.8.7-alpha", root=self.root)
        self.assertIn(__version__, (self.root / "atcgs" / "__init__.py").read_text(encoding="utf-8"))
        self.assertIn(__version__, (self.root / "pixi.toml").read_text(encoding="utf-8"))

    def test_nothing_is_written_when_a_target_is_missing(self):
        (self.root / "ALPHA.md").unlink()
        with self.assertRaisesRegex(bump_version.VersionSyncError, "missing"):
            bump_version.apply_version("9.8.7-alpha", root=self.root)
        self.assertIn(__version__, (self.root / "pixi.toml").read_text(encoding="utf-8"))

    def test_a_dry_run_writes_nothing(self):
        with mock.patch.object(bump_version, "apply_version", side_effect=AssertionError("written")):
            self.assertEqual(bump_version.main(["patch", "--dry-run"]), 0)

    def test_a_level_or_release_is_required(self):
        with self.assertRaises(SystemExit):
            bump_version.main([])


if __name__ == "__main__":
    unittest.main()

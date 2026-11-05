"""`pixi run cgs`: one command; the live ComplexGitSync where it is checked out, the pinned one elsewhere."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cgs import handover  # noqa: E402


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="cgs-launch-"))
        (self.root / "@cgs").mkdir()
        (self.root / "@cgs" / "pixi.toml").write_text("")
        (self.root / "ComplexGitSync").mkdir()
        (self.root / "ComplexGitSync" / "pyproject.toml").write_text("")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.root, True)

    def test_the_development_space_takes_over_where_the_checkout_is(self):
        command = handover(["OPX", "login", "t", "commit", "a message"], {}, self.root)
        self.assertEqual(command, ["pixi", "run", "-m", str(self.root / "@cgs"), "cgs",
                                   "OPX", "login", "t", "commit", "a message"])

    def test_a_clone_without_the_checkout_runs_pinned(self):
        (self.root / "ComplexGitSync" / "pyproject.toml").unlink()
        self.assertIsNone(handover(["--version"], {}, self.root))

    def test_a_clone_without_the_development_manifest_runs_pinned(self):
        (self.root / "@cgs" / "pixi.toml").unlink()
        self.assertIsNone(handover(["--version"], {}, self.root))

    def test_no_loop_inside_the_development_manifest(self):
        env = {"PIXI_PROJECT_ROOT": str(self.root / "@cgs")}
        self.assertIsNone(handover(["--version"], env, self.root))

    def test_pinned_on_request(self):
        self.assertIsNone(handover(["--version"], {"ATCGS_PINNED": "1"}, self.root))


if __name__ == "__main__":
    unittest.main()

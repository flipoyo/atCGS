"""Build name: lower-case(project) by default, configurable in pixi.toml."""
import tempfile
import tomllib
import unittest
from pathlib import Path

from atcgs import ROOT, __version__, build_name, commit_subject


def manifest(body):
    f = Path(tempfile.mkdtemp()) / "pixi.toml"
    f.write_text(body, encoding="utf-8")
    return f


class BuildNameTests(unittest.TestCase):
    def test_repository_build_is_cgs(self):
        self.assertEqual(build_name(), "cgs")
        self.assertEqual(commit_subject("x"), f"cgs-{__version__} x")

    def test_default_is_lower_case_project(self):
        self.assertEqual(build_name(manifest('[tool.cgs]\nproject = "CGS"\n')), "cgs")

    def test_build_name_overrides(self):
        body = '[tool.cgs]\nproject = "CGS"\nbuild-name = "cgitsync"\n'
        self.assertEqual(build_name(manifest(body)), "cgitsync")

    def test_missing_or_invalid_is_refused(self):
        for body in ("", '[tool.cgs]\nbuild-name = "a b"\n'):
            with self.assertRaises(ValueError):
                build_name(manifest(body))


class ConformityTests(unittest.TestCase):
    def test_cgs_files_name_the_project_after_the_build(self):
        for path in ("POEX.cgs", "examples/cgs_opx.cgs", "examples/cgs_dev.cgs", "examples/cgs_usr.cgs"):
            with self.subTest(path=path), (ROOT / path).open("rb") as handle:
                self.assertEqual(tomllib.load(handle)["project"]["name"], build_name())

    def test_alpha_documents_both_names_of_the_one_build(self):
        text = " ".join((ROOT / "ALPHA.md").read_text(encoding="utf-8").split())
        self.assertIn("`@cgs` and `cgitsync` are two names for that one build", text)


if __name__ == "__main__":
    unittest.main()

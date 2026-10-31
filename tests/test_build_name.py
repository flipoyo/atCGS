"""Build name: lower-case(project) by default, configurable in pixi.toml."""
import tempfile
import unittest
from pathlib import Path

from atcgs import __version__, build_name, commit_subject


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


if __name__ == "__main__":
    unittest.main()

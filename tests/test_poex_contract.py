"""Offline POEX 0000 contract checks (no network, no release side effects)."""

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMITIVE = (
    ("CGS-ALPHA", ("ComplexGraphSync", "M.m.p", "@cgs")),
    ("@cgs", ("@cgitsync", "ComplexGitSync", "M.m.p", ".opx")),
    (".opx", (".dev", ".computo", ".omniscience", ".dev")),
    (".dev", (".usr", ".omniscience", ".gts")),
    (".usr", (".omniscience", ".cgs", ".gts")),
)
RELEASE = {"name": "POEX", "id": "0000", "license": "Apache-2.0", "artifact": ".cgs"}


class PoexContractTests(unittest.TestCase):
    def test_exact_tuple_order_and_spelling(self):
        with (ROOT / "POEX.0000.toml").open("rb") as fp:
            spec = tomllib.load(fp)
        self.assertEqual(
            tuple((key, tuple(value)) for key, value in spec["primitive"].items()),
            PRIMITIVE,
        )
        self.assertEqual(spec["release"], RELEASE)
        self.assertEqual(spec["primitive"][".opx"].count(".dev"), 2)

    def test_cgs_root_is_public_and_minimal(self):
        with (ROOT / "POEX.cgs").open("rb") as fp:
            spec = tomllib.load(fp)
        self.assertEqual(tuple(spec.keys()), ("project", "repos"))
        self.assertEqual(spec["project"]["name"], "cgs")
        self.assertEqual(spec["project"]["default_branch"], "main")
        self.assertEqual(len(spec["repos"]), 1)
        root, = spec["repos"]
        self.assertEqual(root["repository"], "github:flipoyo/atCGS")
        self.assertEqual(root["relative_path"], ".")
        self.assertEqual(root["nested_config"], "disabled")
        self.assertNotIn("private", root)
        self.assertNotIn("writable", root)


if __name__ == "__main__":
    unittest.main()

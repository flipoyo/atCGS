"""cgs_{opx,dev,usr}.cgs layer trees and their agreement with ComplexGitSync.

Runs under Pixi, where the pinned ComplexGitSync is installed: every tree is
validated by cgitsync's own parser, not by a copy of its rules.
"""

import tomllib
import unittest
from pathlib import Path

from ComplexGitSync.tree.cgs_format import CgsDocument
from ComplexGitSync.tree.environment_spec import Requirements, validate_environment_declaration

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("opx", "dev", "usr")
# The pinned ComplexGitSync pixi.toml (rev in atCGS pixi.toml) declares these.
CGS_CHANNELS = ["conda-forge"]
CGS_PLATFORMS = ["linux-64", "win-64", "osx-arm64"]
CGS_DEPENDENCIES = {"python": "3.11.*", "pytest": "*", "ruff": "*", "hypothesis": "*"}
CGS_LINT = ["E4", "E7", "E9", "F", "I", "C90"]


def load(layer):
    path = ROOT / "examples" / f"cgs_{layer}.cgs"
    with path.open("rb") as handle:
        return path, tomllib.load(handle)


def by_path(data):
    return {repo.get("relative_path", "."): repo for repo in data["repos"]}


class LayerTreeTests(unittest.TestCase):
    def test_cgitsync_accepts_every_tree(self):
        for layer in LAYERS:
            path, data = load(layer)
            with self.subTest(layer=layer):
                document = CgsDocument.from_toml(path)
                document.validate()
                self.assertEqual(validate_environment_declaration(data, data["repos"]), [])
        CgsDocument.from_toml(ROOT / "POEX.cgs").validate()

    def test_one_project_on_the_alpha_branch_for_every_level(self):
        with (ROOT / "POEX.cgs").open("rb") as handle:
            name = tomllib.load(handle)["project"]["name"]
        for layer in LAYERS:
            _, data = load(layer)
            with self.subTest(layer=layer):
                self.assertEqual(
                    data["project"],
                    {"name": name, "default_branch": "CGS-ALPHA", "fallback_branch": "main"},
                )
                root = by_path(data)["."]
                self.assertEqual(root["repository"], "github:flipoyo/atCGS")
                self.assertEqual(root["nested_config"], "disabled")

    def test_no_tree_mounts_complexgitsync(self):
        # .cgitsync is cgitsync's own directory, never a mount point of the tree.
        for layer in LAYERS:
            mounts = by_path(load(layer)[1])
            with self.subTest(layer=layer):
                self.assertNotIn(".cgitsync", mounts)
                self.assertNotIn(".computo", mounts)
                self.assertFalse(any(r["repository"] == "github:flipoyo/ComplexGitSync" for r in mounts.values()))

    def test_omniscience_is_the_gx4g_ledger_written_at_opx_only(self):
        ledger = dict(by_path(load("opx")[1])[".omniscience"])
        ledger.pop("relative_path")
        # A writable repository takes cgs_<branch> from the project, never a fixed branch.
        self.assertEqual(ledger, {"repository": "codeberg:GX4G/.omniscience", "fallback_branch": "main",
                                  "private": True, "writable": True, "nested_config": "disabled"})
        for layer in ("dev", "usr"):
            with self.subTest(layer=layer):
                self.assertNotIn(".omniscience", by_path(load(layer)[1]))

    def test_agentic_structure_follows_complexgitsync(self):
        distant = {".agent/.distant/ticket", ".agent/.distant/dev-sync", ".agent/.distant/documentation"}
        local = {".agent/.local/.dev", ".agent/.local/.localSpec", ".agent/.local/.claude"}
        for layer in LAYERS:
            mounts = by_path(load(layer)[1])
            with self.subTest(layer=layer):
                agent = {path for path in mounts if path.startswith(".agent/")}
                self.assertEqual(agent, {"opx": distant | local, "dev": distant | local, "usr": set()}[layer])
                for path in agent & distant:
                    self.assertTrue(mounts[path]["private"])
                    self.assertNotIn("writable", mounts[path])
                for path in agent & local:
                    self.assertTrue(mounts[path]["private"])
                    self.assertIs(mounts[path]["writable"], True)
                    self.assertNotIn("default_branch", mounts[path])

    def test_opx_and_dev_write_and_usr_mounts_nothing_private(self):
        for layer in LAYERS:
            repos = load(layer)[1]["repos"]
            with self.subTest(layer=layer):
                writes = any(repo.get("writable") for repo in repos)
                self.assertEqual(writes, layer != "usr")
        self.assertFalse(any(repo.get("private") for repo in load("usr")[1]["repos"]))


class EnvironmentAgreementTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "pixi.toml").open("rb") as handle:
            self.pixi = tomllib.load(handle)

    def test_pixi_agrees_with_complexgitsync(self):
        workspace = self.pixi["workspace"]
        self.assertEqual(workspace["channels"], CGS_CHANNELS)
        self.assertEqual(workspace["platforms"], CGS_PLATFORMS)
        # ComplexGitSync's dependencies, plus only what the C microcodes and wallet tests need.
        self.assertEqual(self.pixi["dependencies"], {**CGS_DEPENDENCIES, "c-compiler": "*"})
        self.assertEqual(self.pixi["target"], {"unix": {"dependencies": {"openssh": "*"}}})
        pin = self.pixi["pypi-dependencies"]["complexgitsync"]
        self.assertEqual(pin["git"], "https://github.com/flipoyo/ComplexGitSync.git")
        self.assertRegex(pin["rev"], r"^[0-9a-f]{40}$")

    def test_lint_contract_matches_complexgitsync(self):
        with (ROOT / "ruff.toml").open("rb") as handle:
            ruff = tomllib.load(handle)
        self.assertEqual(ruff["lint"]["select"], CGS_LINT)
        self.assertEqual((ruff["line-length"], ruff["target-version"]), (100, "py311"))

    def test_every_command_is_a_pixi_task(self):
        tasks = self.pixi["tasks"]
        for name in ("@cgs", "test", "lint", "contract-inspect", "contract-candidate",
                     "poex-candidate", "microcode-test"):
            with self.subTest(task=name):
                self.assertTrue(tasks[name].startswith("python ") or name == "lint")

    def test_trees_require_the_pixi_environment(self):
        python = self.pixi["dependencies"]["python"].removesuffix(".*")
        declared = set()
        for layer in LAYERS:
            path, _ = load(layer)
            requirements = Requirements.from_cgs(CgsDocument.from_toml(path))
            with self.subTest(layer=layer):
                self.assertEqual(requirements.environment_root, "root")
                self.assertIn("pixi.toml", requirements.manifest_patterns)
                tools = {item.name: item.minimum_version for item in requirements.dependencies}
                self.assertEqual(tools["python"], python)
                self.assertIn("pixi", tools)
                declared.add(requirements)
        self.assertEqual(len(declared), 1, "the three levels must declare one environment")


if __name__ == "__main__":
    unittest.main()

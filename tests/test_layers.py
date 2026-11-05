"""cgs-{opx,dev,usr}.cgs layer trees and their agreement with ComplexGitSync.

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
    path = ROOT / "examples" / f"cgs-{layer}.cgs"
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
                # LinkAtCGS §7: cgs-<level>.cgs opens its project on branch <level>, then CGS-ALPHA.
                self.assertEqual(
                    data["project"],
                    {"name": name, "default_branch": layer, "fallback_branch": "CGS-ALPHA"},
                )
                root = by_path(data)["."]
                self.assertEqual(root["repository"], "github:flipoyo/atCGS")
                self.assertEqual(root["nested_config"], "disabled")

    def test_complexgitsync_is_the_live_checkout_at_opx_and_dev_only(self):
        # .cgitsync is cgitsync's own directory, never a mount point of the tree.
        # OPX and DEV mount ./ComplexGitSync, the editable path of @cgs/pixi.toml.
        for layer in LAYERS:
            mounts = by_path(load(layer)[1])
            with self.subTest(layer=layer):
                self.assertNotIn(".cgitsync", mounts)
                self.assertNotIn(".computo", mounts)
                at = [p for p, r in mounts.items() if r["repository"] == "github:flipoyo/ComplexGitSync"]
                if layer == "usr":
                    self.assertEqual(at, [])
                    continue
                self.assertEqual(at, ["ComplexGitSync"])
                self.assertEqual(mounts["ComplexGitSync"]["fallback_branch"], "CGS-ALPHA")
        with (ROOT / "@cgs" / "pixi.toml").open("rb") as handle:
            live = tomllib.load(handle)["pypi-dependencies"]["complexgitsync"]
        self.assertEqual(live["path"], "../ComplexGitSync")  # ./ComplexGitSync, from @cgs/

    def test_omniscience_is_the_ledger_written_at_opx_only(self):
        ledger = dict(by_path(load("opx")[1])[".omniscience"])
        ledger.pop("relative_path")
        # A writable repository takes cgs_<branch> from the project, never a fixed branch.
        self.assertEqual(ledger, {"repository": "github:flipoyo/omniscience", "fallback_branch": "main",
                                  "private": True, "writable": True, "nested_config": "disabled"})
        for layer in ("dev", "usr"):
            with self.subTest(layer=layer):
                self.assertNotIn(".omniscience", by_path(load(layer)[1]))

    def test_the_register_is_in_omniscience_not_in_cgitsync(self):
        from atcgs.commands import REGISTER

        self.assertEqual(REGISTER, ROOT / ".cgitsync" / ".memory" / ".register")
        for layer in LAYERS:
            mounts = by_path(load(layer)[1])
            with self.subTest(layer=layer):
                cgitsync = {path for path in mounts if path.startswith(".cgitsync")}
                self.assertEqual(cgitsync, {".cgitsync/.memory"} if layer != "usr" else set())
                self.assertFalse(any("register" in r["repository"] for r in mounts.values()))

    def test_opx_and_dev_declare_the_memory_memory_setup_proposes(self):
        # The cgitsync >= 8.7.1 entry: no default_branch, the branch is derived (MemorySetupBranch).
        for layer in ("opx", "dev"):
            memory = dict(by_path(load(layer)[1])[".cgitsync/.memory"])
            with self.subTest(layer=layer):
                self.assertEqual(memory, {"repository": "github:flipoyo/.memory", "relative_path": ".cgitsync/.memory",
                                          "fallback_branch": "main", "private": True, "writable": True,
                                          "nested_config": "disabled"})

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
        # ComplexGitSync's dependencies, plus only the identity layer's cryptography.
        self.assertEqual(self.pixi["dependencies"], {**CGS_DEPENDENCIES, "cryptography": ">=44"})
        self.assertEqual(self.pixi["target"], {"unix": {"dependencies": {"openssh": "*"}}})
        self.assertNotIn("feature", self.pixi)  # one source of ComplexGitSync per manifest
        self.assertNotIn("environments", self.pixi)
        pin = self.pixi["pypi-dependencies"]["complexgitsync"]
        self.assertEqual(pin["git"], "https://github.com/flipoyo/ComplexGitSync.git")
        self.assertRegex(pin["rev"], r"^[0-9a-f]{40}$")

    def test_the_cgs_manifest_is_the_root_one_with_complexgitsync_live(self):
        with (ROOT / "@cgs" / "pixi.toml").open("rb") as handle:
            dev = tomllib.load(handle)
        self.assertEqual(dev["pypi-dependencies"], {"complexgitsync": {"path": "../ComplexGitSync", "editable": True}})
        for table in ("dependencies", "target"):
            with self.subTest(table=table):
                self.assertEqual(dev[table], self.pixi[table])
        for key in ("version", "channels", "platforms"):
            with self.subTest(key=key):
                self.assertEqual(dev["workspace"][key], self.pixi["workspace"][key])
        # the same tasks, run from atCGS's root; only `cgs` differs: the root's hands over to this one
        dev_tasks = {name: task["cmd"] for name, task in dev["tasks"].items()}
        self.assertEqual(dev_tasks.pop("cgs"), "python -m atcgs")
        root_tasks = dict(self.pixi["tasks"])
        self.assertEqual(root_tasks.pop("cgs"), "python scripts/cgs.py")
        self.assertEqual(dev_tasks, root_tasks)
        self.assertEqual({task["cwd"] for task in dev["tasks"].values()}, {".."})

    def test_the_root_manifest_never_names_the_checkout(self):
        text = (ROOT / "pixi.toml").read_text(encoding="utf-8")
        self.assertNotIn("path =", text)
        lock = (ROOT / "pixi.lock").read_text(encoding="utf-8")
        self.assertNotIn("ComplexGitSync\n", lock.replace("/ComplexGitSync.git", ""))
        self.assertNotIn("editable: true", lock)

    def test_lint_contract_matches_complexgitsync(self):
        with (ROOT / "ruff.toml").open("rb") as handle:
            ruff = tomllib.load(handle)
        self.assertEqual(ruff["lint"]["select"], CGS_LINT)
        self.assertEqual((ruff["line-length"], ruff["target-version"]), (100, "py311"))

    def test_every_command_is_a_pixi_task(self):
        tasks = self.pixi["tasks"]
        for name in ("cgs", "test", "lint", "contract-inspect", "identity-demo", "local-remote"):
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


class OpFrontierSharedTests(unittest.TestCase):
    """Dogfooding S4: atCGS takes its levels and codes from ComplexGitSync, one definition."""

    def test_levels_and_codes_are_the_poe_of_complexgitsync(self):
        from ComplexGitSync.orchestre.op_levels import LEVELS

        import atcgs
        from atcgs.commands import ROLE_CODES

        self.assertEqual(atcgs.PRIME_CGS, tuple(LEVELS))
        self.assertEqual(ROLE_CODES, {"OPX": "0000", "DEV": "1000", "USR": "1100", "PUB": "1111"})

    def test_workspace_spec_is_a_plain_project_not_a_level_file(self):
        from ComplexGitSync.tree.named_cgs import NamedCgs

        path = ROOT / "examples" / "ComplexGraphSync.cgs"
        self.assertIsNone(NamedCgs.parse(path))
        document = CgsDocument.from_toml(path)
        document.validate()
        self.assertEqual(document.project_name, "ComplexGraphSync")
        self.assertEqual(document.default_branch, "CGS-ALPHA")

    def test_workspace_spec_agrees_with_complexgitsync_copy(self):
        copy = ROOT / "ComplexGitSync" / "examples" / "cgs-opx.cgs"
        if not copy.exists():
            self.skipTest("the ComplexGitSync checkout is not here")

        def body(path):
            text = path.read_text(encoding="utf-8")
            return text[text.index("project = "):]

        self.assertEqual(body(ROOT / "examples" / "ComplexGraphSync.cgs"), body(copy))

class MolonariTreeTests(unittest.TestCase):
    """examples/molonari.cgs: MOLONARI on CGS-MOLO, with a read-only atCGS as its gate."""

    path = ROOT / "examples" / "molonari.cgs"
    MOLONARI = ("MOLONARI1D", "MOLONARI-API", "MOLONARI-data", "MOLONARI-hardware", "MOLONARI-gate", "MOLONARI-computo")

    def load(self):
        with self.path.open("rb") as handle:
            data = tomllib.load(handle)
        return data, {repo["repository"]: repo for repo in data["repos"]}

    def test_cgitsync_accepts_the_tree(self):
        document = CgsDocument.from_toml(self.path)
        document.validate()
        self.assertEqual((document.project_name, document.default_branch), ("MOLONARI", "CGS-MOLO"))

    def test_no_environment_is_declared_so_molonari1d_is_not_relocked(self):
        data, _ = self.load()
        self.assertNotIn("environment", data)
        self.assertNotIn("environment_root", data)

    def test_the_six_molonari_repositories_follow_cgs_molo(self):
        _, repos = self.load()
        for name in self.MOLONARI:
            with self.subTest(repo=name):
                repo = repos[f"github:flipoyo/{name}"]
                self.assertEqual((repo["default_branch"], repo["fallback_branch"]), ("CGS-MOLO", "main"))
                self.assertNotIn("private", repo)
        self.assertEqual(repos["github:flipoyo/MOLONARI1D"]["relative_path"], ".")

    def test_atcgs_is_the_read_only_gate_and_complexgitsync_is_not_mounted(self):
        _, repos = self.load()
        gate = repos["github:flipoyo/atCGS"]
        self.assertEqual((gate["relative_path"], gate["default_branch"]), (".atcgs", "CGS-ALPHA"))
        self.assertTrue(gate["private"])
        self.assertNotIn("writable", gate)
        self.assertNotIn("github:flipoyo/ComplexGitSync", repos)

    def test_the_register_is_writable_and_the_identities_are_read_only_on_cgs_molo(self):
        _, repos = self.load()
        memory = repos["github:flipoyo/.memory"]
        self.assertEqual(memory["relative_path"], ".cgitsync/.memory")
        self.assertTrue(memory["private"] and memory["writable"])
        published = repos["github:flipoyo/omniscience"]
        self.assertEqual((published["relative_path"], published["default_branch"]), (".omniscience", "CGS-MOLO"))
        self.assertTrue(published["private"])
        self.assertNotIn("writable", published)

    def test_complexgitsync_copy_names_the_same_molonari_repositories(self):
        copy = ROOT / "ComplexGitSync" / "examples" / "molonari.cgs"
        if not copy.exists():
            self.skipTest("the ComplexGitSync checkout is not here")
        with copy.open("rb") as handle:
            theirs = {r["repository"] for r in tomllib.load(handle)["repos"]}
        _, repos = self.load()
        self.assertEqual({f"github:flipoyo/{n}" for n in self.MOLONARI}, theirs - {"github:flipoyo/ComplexGitSync"})
        self.assertLessEqual({f"github:flipoyo/{n}" for n in self.MOLONARI}, set(repos))


if __name__ == "__main__":
    unittest.main()

"""examples/cgs-alpha.cgs, the one workspace tree, and its agreement with ComplexGitSync.

Runs under Pixi, where the pinned ComplexGitSync is installed: every tree is
validated by cgitsync's own parser, not by a copy of its rules.
"""

import tomllib
import unittest
from pathlib import Path

from ComplexGitSync.tree.cgs_format import CgsDocument
from ComplexGitSync.tree.environment_spec import Requirements, validate_environment_declaration

ROOT = Path(__file__).resolve().parents[1]
# The pinned ComplexGitSync pixi.toml (rev in atCGS pixi.toml) declares these.
CGS_CHANNELS = ["conda-forge"]
CGS_PLATFORMS = ["linux-64", "win-64", "osx-arm64"]
CGS_DEPENDENCIES = {"python": "3.11.*", "pytest": "*", "ruff": "*", "hypothesis": "*"}
CGS_LINT = ["E4", "E7", "E9", "F", "I", "C90"]


def load():
    path = ROOT / "examples" / "cgs-alpha.cgs"
    with path.open("rb") as handle:
        return path, tomllib.load(handle)


def by_path(data):
    return {repo.get("relative_path", "."): repo for repo in data["repos"]}


class LayerTreeTests(unittest.TestCase):
    def test_cgitsync_accepts_the_tree(self):
        path, data = load()
        document = CgsDocument.from_toml(path)
        document.validate()
        self.assertEqual(validate_environment_declaration(data, data["repos"]), [])
        CgsDocument.from_toml(ROOT / "POEX.cgs").validate()

    def test_the_workspace_is_project_cgs_on_the_alpha_branch_and_no_level_file_remains(self):
        from ComplexGitSync.tree.named_cgs import NamedCgs

        with (ROOT / "POEX.cgs").open("rb") as handle:
            name = tomllib.load(handle)["project"]["name"]
        path, data = load()
        self.assertEqual(data["project"], {"name": name, "default_branch": "CGS-ALPHA"})
        self.assertIsNone(NamedCgs.parse(path))  # `alpha` has five characters: not a level file
        self.assertEqual(sorted(p.name for p in (ROOT / "examples").glob("cgs-*.cgs")), ["cgs-alpha.cgs"])
        root = by_path(data)["."]
        self.assertEqual(root["repository"], "github:flipoyo/atCGS")
        self.assertEqual(root["nested_config"], "disabled")

    def test_complexgitsync_is_the_live_checkout(self):
        # .cgitsync is cgitsync's own directory, never a mount point of the tree.
        mounts = by_path(load()[1])
        self.assertNotIn(".cgitsync", mounts)
        self.assertNotIn(".computo", mounts)
        at = [p for p, r in mounts.items() if r["repository"] == "github:flipoyo/ComplexGitSync"]
        self.assertEqual(at, ["ComplexGitSync"])
        self.assertEqual(mounts["ComplexGitSync"]["fallback_branch"], "CGS-ALPHA")
        with (ROOT / "@cgs" / "pixi.toml").open("rb") as handle:
            live = tomllib.load(handle)["pypi-dependencies"]["complexgitsync"]
        self.assertEqual(live["path"], "../ComplexGitSync")  # ./ComplexGitSync, from @cgs/

    def test_omniscience_is_the_ledger_written_by_the_owner(self):
        ledger = dict(by_path(load()[1])[".omniscience"])
        ledger.pop("relative_path")
        # A writable repository takes cgs_<branch> from the project, never a fixed branch.
        self.assertEqual(ledger, {"repository": "github:flipoyo/omniscience", "fallback_branch": "main",
                                  "private": True, "writable": True, "nested_config": "disabled"})

    def test_the_register_is_in_the_memory_not_in_cgitsync(self):
        from atcgs.commands import REGISTER

        self.assertEqual(REGISTER, ROOT / ".cgitsync" / ".memory" / ".register")
        mounts = by_path(load()[1])
        self.assertEqual({path for path in mounts if path.startswith(".cgitsync")}, {".cgitsync/.memory"})
        self.assertFalse(any("register" in r["repository"] for r in mounts.values()))

    def test_the_memory_is_the_one_memory_setup_proposes(self):
        # The cgitsync >= 8.7.1 entry: no default_branch, the branch is derived (MemorySetupBranch).
        memory = dict(by_path(load()[1])[".cgitsync/.memory"])
        self.assertEqual(memory, {"repository": "github:flipoyo/.memory", "relative_path": ".cgitsync/.memory",
                                  "fallback_branch": "main", "private": True, "writable": True,
                                  "nested_config": "disabled"})

    def test_agentic_structure_follows_complexgitsync(self):
        distant = {".agent/.distant/ticket", ".agent/.distant/dev-sync", ".agent/.distant/documentation"}
        local = {".agent/.local/.dev", ".agent/.local/.localSpec", ".agent/.local/.claude"}
        mounts = by_path(load()[1])
        agent = {path for path in mounts if path.startswith(".agent/")}
        self.assertEqual(agent, distant | local)
        for path in agent & distant:
            self.assertTrue(mounts[path]["private"])
            self.assertNotIn("writable", mounts[path])
        for path in agent & local:
            self.assertTrue(mounts[path]["private"])
            self.assertIs(mounts[path]["writable"], True)
            self.assertNotIn("default_branch", mounts[path])


class EnvironmentAgreementTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "pixi.toml").open("rb") as handle:
            self.pixi = tomllib.load(handle)

    def test_pixi_agrees_with_complexgitsync(self):
        workspace = self.pixi["workspace"]
        self.assertEqual(workspace["channels"], CGS_CHANNELS)
        self.assertEqual(workspace["platforms"], CGS_PLATFORMS)
        # ComplexGitSync's dependencies, plus only the identity layer's cryptography and the Owner's gh.
        self.assertEqual(self.pixi["dependencies"], {**CGS_DEPENDENCIES, "cryptography": ">=44", "gh": "*"})
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

    def test_the_tree_requires_the_pixi_environment(self):
        python = self.pixi["dependencies"]["python"].removesuffix(".*")
        path, _ = load()
        requirements = Requirements.from_cgs(CgsDocument.from_toml(path))
        self.assertEqual(requirements.environment_root, "root")
        self.assertIn("pixi.toml", requirements.manifest_patterns)
        tools = {item.name: item.minimum_version for item in requirements.dependencies}
        self.assertEqual(tools["python"], python)
        self.assertIn("pixi", tools)


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

class MolonariTwinTests(unittest.TestCase):
    """examples/molo_*.cgs: the MOLONARI twins on CGS-MOLO, each with a read-only atCGS as its gate."""

    SUBTWINS = {"molo_hrdw.cgs": ("MOLO-HRDW", "MOLONARI-hardware"),
                "molo_data.cgs": ("MOLO-DATA", "MOLONARI-data"),
                "molo_cmpt.cgs": ("MOLO-CMPT", "MOLONARI-computo")}
    GATE = {"github:flipoyo/atCGS", "github:flipoyo/.memory", "github:flipoyo/omniscience"}

    def load(self, name):
        with (ROOT / "examples" / name).open("rb") as handle:
            data = tomllib.load(handle)
        return data, {repo["repository"]: repo for repo in data["repos"]}

    def names(self):
        return [*self.SUBTWINS, "molo_twx.cgs"]

    def test_cgitsync_accepts_every_twin_and_none_is_read_as_a_level_file(self):
        from ComplexGitSync.tree.named_cgs import NamedCgs

        for name in self.names():
            with self.subTest(twin=name):
                path = ROOT / "examples" / name
                self.assertIsNone(NamedCgs.parse(path))  # molo-twx.cgs would read as project molo, branch twx
                document = CgsDocument.from_toml(path)
                document.validate()
                self.assertEqual(document.default_branch, "CGS-MOLO")

    def test_each_subtwin_is_one_repository_at_its_root(self):
        for name, (project, repo) in self.SUBTWINS.items():
            with self.subTest(twin=name):
                data, repos = self.load(name)
                self.assertEqual(data["project"]["name"], project)
                self.assertEqual(set(repos) - self.GATE, {f"github:flipoyo/{repo}"})
                self.assertEqual(repos[f"github:flipoyo/{repo}"]["relative_path"], ".")

    def test_the_twx_composes_the_subtwins_under_molonari1d(self):
        data, repos = self.load("molo_twx.cgs")
        self.assertEqual(data["project"]["name"], "MOLO-TWX")
        self.assertEqual(repos["github:flipoyo/MOLONARI1D"]["relative_path"], ".")
        self.assertEqual(set(repos) - self.GATE - {"github:flipoyo/MOLONARI1D"},
                         {f"github:flipoyo/{repo}" for _, repo in self.SUBTWINS.values()})

    def test_every_twin_has_the_same_gate(self):
        for name in self.names():
            with self.subTest(twin=name):
                data, repos = self.load(name)
                self.assertNotIn("environment", data)  # each repository keeps its own pixi.lock
                gate = repos["github:flipoyo/atCGS"]
                self.assertEqual((gate["relative_path"], gate["default_branch"], gate["private"]), (".atcgs", "CGS-ALPHA", True))
                self.assertNotIn("writable", gate)
                memory = repos["github:flipoyo/.memory"]
                self.assertTrue(memory["private"] and memory["writable"])
                published = repos["github:flipoyo/omniscience"]
                self.assertEqual((published["relative_path"], published["default_branch"]), (".omniscience", "CGS-MOLO"))
                self.assertNotIn("writable", published)
                self.assertNotIn("github:flipoyo/ComplexGitSync", repos)
                for repo, entry in repos.items():
                    if repo not in self.GATE:
                        self.assertEqual((entry["default_branch"], entry["fallback_branch"]), ("CGS-MOLO", "main"))


if __name__ == "__main__":
    unittest.main()

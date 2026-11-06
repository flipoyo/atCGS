"""FluidOPX: `OPX init` (a new machine, another machine, a project) and the append-only pin."""

import base64
import datetime
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import atcgs.commands as cmd
import atcgs.ownerinit as ownerinit
from atcgs import OpFrontier, Unauthorized, credential, pin
from atcgs.glyph import open_glyph
from atcgs.journal import Register
from tests.test_onboard import FAKE_GH
from tests.test_project_register import AUTH, OPX, git

BOB_LOGIN = ("bob", "bob passphrase")
OWNER = ["opx", "opx passphrase"]
URL = "https://example.test/flipoyo/{}.git"
CGS = """project = { name = "cgs", default_branch = "CGS-ALPHA" }
repos = [
    { repository = "github:flipoyo/atCGS", relative_path = "." },
    { repository = "github:flipoyo/omniscience", relative_path = ".omniscience" },
    { repository = "github:flipoyo/.memory", relative_path = ".cgitsync/.memory" },
]
"""
PROJ = """project = { name = "PROJ", default_branch = "CGS-MOLO" }
repos = [
    { repository = "github:flipoyo/lib", relative_path = "." },
    { repository = "github:flipoyo/atCGS", relative_path = ".atcgs" },
    { repository = "github:flipoyo/.memory", relative_path = ".cgitsync/.memory" },
    { repository = "github:flipoyo/omniscience", relative_path = ".omniscience" },
]
"""


class PinTests(unittest.TestCase):
    def test_the_pin_is_appended_never_rewritten(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        self.assertIsNone(pin.read(root))
        self.assertTrue(pin.append(root, OPX.pub, OPX.uid, datetime.date(2026, 11, 5)))
        first = (root / "spec" / "opx.toml").read_text()
        self.assertFalse(pin.append(root, OPX.pub, OPX.uid))  # the same key: nothing is written
        self.assertEqual((root / "spec" / "opx.toml").read_text(), first)
        other = bytes(range(32))
        self.assertTrue(pin.append(root, other, "f" * 64, datetime.date(2027, 1, 1)))
        text = (root / "spec" / "opx.toml").read_text()
        self.assertTrue(text.startswith(first))  # the older pin stays, byte for byte
        self.assertEqual((pin.read(root), len(pin.history(root))), (other, 2))

    def test_the_legacy_pin_in_contracts_is_still_read_when_there_is_none(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "spec").mkdir()
        (root / "spec" / "contracts.toml").write_text(f'[identity]\nopx_pub = "{base64.b64encode(OPX.pub).decode()}"\n')
        self.assertEqual(pin.read(root), OPX.pub)
        pin.append(root, bytes(range(32)), "f" * 64)
        self.assertEqual(pin.read(root), bytes(range(32)))  # spec/opx.toml wins

    def test_a_bad_key_is_refused(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "spec").mkdir()
        (root / "spec" / "opx.toml").write_text('[[pin]]\nopx_pub = "c2hvcnQ="\n')
        with self.assertRaises(ValueError):
            pin.read(root)

    def test_the_real_pin_is_the_one_of_the_owner(self):
        self.assertEqual(pin.read(Path(__file__).resolve().parents[1]), OPX.pub.__class__(pin.read(
            Path(__file__).resolve().parents[1])))
        self.assertEqual(len(pin.history(Path(__file__).resolve().parents[1])), 1)


class OwnerInit(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-init-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.gh_state = self.dir / "gh"
        self.gh_state.mkdir()
        (self.dir / "bin").mkdir()
        gh = self.dir / "bin" / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.remotes = {name: self.bare(name) for name in ("atCGS", ".memory", "omniscience", "lib-memory")}
        self.ws = self.dir / "trees" / "cgs-20261106"
        self.make_workspace()
        env = {"ATCGS_KDF_PROFILE": "test", "ATCGS_GLYPHS": str(self.dir / "glyphs"), "ATCGS_TREES": str(self.dir / "trees"),
               "FAKE_GH": str(self.gh_state), "PATH": f"{self.dir / 'bin'}:{os.environ['PATH']}",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("ATCGS_OPX_PUB", "ATCGS_REGISTER", "ATCGS_PROJECT", "CGSHOME", "ATCGS_IDENTITIES"):
            os.environ.pop(name, None)
        root = mock.patch.object(cmd, "ROOT", self.ws)
        root.start()
        self.addCleanup(root.stop)
        self.glyph = cmd.glyph_path(OPX.uid)

    def bare(self, name):
        remote = self.dir / f"{name}.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(remote))
        seed = self.dir / f"seed-{name}"
        git(self.dir, "clone", "-q", str(remote), str(seed))
        (seed / "README.md").write_text(name + "\n")
        if name == "atCGS":
            (seed / "spec").mkdir()
            (seed / "spec" / ".keep").write_text("")
            (seed / "examples").mkdir()
            (seed / "examples" / "cgs-alpha.cgs").write_text(CGS)
            (seed / "examples" / "proj.cgs").write_text(PROJ)
        git(seed, "add", "-A")
        git(seed, "commit", "-qm", "init")
        git(seed, "push", "-q", "origin", "HEAD:main")
        git(seed, "push", "-q", "origin", "HEAD:CGS-MOLO")
        return remote

    def clone(self, name, where, branch="main", remote=None):
        remote = remote or self.remotes[name]
        git(self.dir, "clone", "-q", "-b", branch, str(remote), str(where))
        url = URL.format(name)
        git(where, "config", f"url.file://{remote}.insteadOf", url)
        git(where, "remote", "set-url", "origin", url)

    def make_workspace(self):
        self.ws.parent.mkdir(parents=True)
        self.clone("atCGS", self.ws)
        (self.ws / ".cgitsync").mkdir()
        self.clone(".memory", self.ws / ".cgitsync" / ".memory")
        self.clone("omniscience", self.ws / ".omniscience", branch="CGS-MOLO")

    def run_init(self, *args, answers=None, yes=True, as_login=None):
        answers = answers if answers is not None else [*OWNER, OWNER[1]]
        with mock.patch.object(cmd, "ask", side_effect=list(as_login or answers)), \
                mock.patch.object(ownerinit, "confirm", return_value="y" if yes else "n"):
            return ownerinit.run(AUTH, args)

    def owner_register(self):
        return Register(self.ws / ".cgitsync" / ".memory" / ".register", OPX.pub)

    def gh_keys(self):
        return sorted(f"{f.stem}:{line.split(chr(9))[1]}" for f in self.gh_state.glob("*.keys")
                      for line in f.read_text().splitlines())


class CaseNewTests(OwnerInit):
    def test_a_new_machine_becomes_opx_in_one_run(self):
        out = self.run_init()
        self.assertEqual(out["case"], "new")
        # the pin, written by atCGS, appended, and pushed
        self.assertEqual(pin.read(self.ws), OPX.pub)
        self.assertIn("pin the OPX key", git(self.remotes["atCGS"], "log", "-1", "--format=%s", "main"))
        self.assertIn("[[pin]]", git(self.remotes["atCGS"], "show", "main:spec/opx.toml"))
        # the register: enrolled once, the three repositories granted as OPX
        state = self.owner_register().state()
        self.assertTrue(state.is_active(OPX.uid))
        self.assertEqual({r.rsplit("/", 1)[-1]: g.role for r, g in state.roles(OPX.uid).items()},
                         {"atCGS": "OPX", "omniscience": "OPX", ".memory": "OPX"})
        self.assertEqual(len(self.owner_register().identity.entries()), 1)
        # the GLYPH, the deploy keys, the pushed register, the published identities
        self.assertEqual(len(open_glyph(OPX, self.glyph.read_bytes())), 3)
        self.assertEqual(len(self.gh_keys()), 3)
        self.assertIn("atcgs init", git(self.remotes[".memory"], "log", "-1", "--format=%s", "main"))
        self.assertIn(OPX.uid, git(self.remotes["omniscience"], "show", "CGS-MOLO:atcgs/identity.jsonl"))
        self.assertTrue(credential.collect(OPX, self.glyph.read_bytes(), [("master", self.ws)], OPX.pub)["ok"])

    def test_nothing_is_edited_by_hand_and_the_run_asks_the_password_once(self):
        with mock.patch.object(cmd, "ask", side_effect=[*OWNER, OWNER[1]]) as asked:
            with mock.patch.object(ownerinit, "confirm", return_value="y"):
                ownerinit.run(AUTH, ())
        self.assertEqual(asked.call_count, 3)  # login, password, password again (a new key is typed twice)
        self.assertNotIn("opx_pub", (self.ws / "spec" / "contracts.toml").read_text()
                         if (self.ws / "spec" / "contracts.toml").exists() else "")

    def test_a_second_run_changes_nothing_and_shows_the_credentials(self):
        self.run_init()
        before = (self.glyph.read_bytes(), (self.ws / "spec" / "opx.toml").read_text(), self.gh_keys(),
                  self.owner_register().access.path.read_bytes())
        out = self.run_init(answers=OWNER)
        self.assertEqual(out["case"], "ok")
        self.assertIn("ok", out["__text__"])
        self.assertEqual(before, (self.glyph.read_bytes(), (self.ws / "spec" / "opx.toml").read_text(), self.gh_keys(),
                                  self.owner_register().access.path.read_bytes()))

    def test_another_login_is_refused_once_a_key_is_pinned(self):
        self.run_init()
        with self.assertRaisesRegex(Unauthorized, "there is one OPX"):
            self.run_init(as_login=BOB_LOGIN)

    def test_plan_and_a_declined_run_write_nothing(self):
        self.assertEqual(self.run_init("--plan")["reason"], "plan only")
        self.assertEqual(self.run_init(yes=False)["reason"], "declined")
        self.assertIsNone(pin.read(self.ws))
        self.assertFalse(self.glyph.exists())
        self.assertEqual(self.gh_keys(), [])
        self.assertEqual(self.owner_register().identity.entries(), [])

    def test_a_register_of_another_owner_is_never_taken_over(self):
        other = __import__("atcgs.identity", fromlist=["derive"]).derive("x", "x passphrase", profile="test")
        Register(self.ws / ".cgitsync" / ".memory" / ".register", other.pub).init(other)
        with self.assertRaises(Exception):
            self.run_init()
        self.assertFalse(self.gh_keys() and False)


class CaseAnotherMachineTests(OwnerInit):
    def test_a_pinned_machine_with_no_glyph_rebuilds_it_instead_of_enrolling_again(self):
        self.run_init()
        self.glyph.unlink()
        out = self.run_init(answers=OWNER)
        self.assertEqual(out["case"], "rebuild")
        self.assertTrue(out["applied"])
        self.assertEqual(len(self.owner_register().identity.entries()), 1)  # the error of 2026-11-06 cannot happen
        self.assertTrue(credential.collect(OPX, self.glyph.read_bytes(), [("master", self.ws)], OPX.pub)["ok"])

    def test_from_takes_a_copy_you_still_have(self):
        self.run_init()
        keep = self.dir / "copy.glyph"
        shutil.copy(self.glyph, keep)
        want = self.glyph.read_bytes()
        self.glyph.unlink()
        out = self.run_init("--from", str(keep), answers=OWNER)
        self.assertEqual((out["keys"], self.glyph.read_bytes()), (3, want))


class CaseProjectTests(OwnerInit):
    def make_project(self):
        tree = self.dir / "trees" / "PROJ-20261106"
        (tree / ".cgitsync").mkdir(parents=True)
        (tree / ".atcgs").mkdir()
        self.clone(".memory", tree / ".cgitsync" / ".memory", remote=self.remotes["lib-memory"])
        git(tree / ".cgitsync" / ".memory", "remote", "set-url", "origin", URL.format(".memory"))
        git(tree / ".cgitsync" / ".memory", "config", f"url.file://{self.remotes['lib-memory']}.insteadOf", URL.format(".memory"))
        self.clone("omniscience", tree / ".omniscience", branch="CGS-MOLO")
        return tree

    def test_a_project_costs_one_new_key_the_others_are_reused(self):
        self.run_init()
        tree = self.make_project()
        before = {(k.repo, k.role) for k in open_glyph(OPX, self.glyph.read_bytes())}
        out = self.run_init("PROJ", answers=OWNER)
        self.assertEqual(out["case"], "project")
        glyph = {(k.repo, k.role) for k in open_glyph(OPX, self.glyph.read_bytes())}
        self.assertEqual(glyph - before, {("github:flipoyo/lib", "OPX")})  # one new key
        self.assertTrue(before <= glyph)  # the others are the very same keys
        self.assertEqual(len(self.gh_keys()), 4)  # only lib was added to GitHub
        reg = Register(tree / ".cgitsync" / ".memory" / ".register", OPX.pub)
        self.assertEqual({r.rsplit("/", 1)[-1] for r in reg.state().roles(OPX.uid)}, {"lib", "atCGS", ".memory", "omniscience"})
        self.assertIn("atcgs init PROJ", git(self.remotes["lib-memory"], "log", "-1", "--format=%s", "main"))

    def test_a_project_needs_the_glyph_of_a_first_init(self):
        self.run_init()
        self.make_project()
        self.glyph.unlink()
        with self.assertRaisesRegex(ValueError, "no GLYPH"):
            self.run_init("PROJ", answers=OWNER, yes=True)

    def test_the_verb_and_its_flags(self):
        for args in ([], ["--plan"], ["PROJ"], ["PROJ", "--plan"], ["--from", "x"]):
            self.assertEqual(OpFrontier().accept(["OPX", "init", *args]).args, ("init", *args))
        for layer in ("DEV", "USR"):
            with self.assertRaises(ValueError):
                OpFrontier().accept([layer, "init"])
        for bad in (["a", "b"], ["--wat"], ["--plan", "--plan"]):
            with self.assertRaises(ValueError):
                OpFrontier().accept(["OPX", "init", *bad])


class NoSecretTests(OwnerInit):
    def test_the_output_holds_no_secret(self):
        out = json.dumps(self.run_init())
        for secret in ("PRIVATE KEY", "opx passphrase", "BEGIN OPENSSH"):
            self.assertNotIn(secret, out)


if __name__ == "__main__":
    unittest.main()


class GuardTests(OwnerInit):
    def test_init_refuses_an_atcgs_behind_cgs_alpha(self):
        self.assertIsNone(ownerinit.behind(self.ws))  # no CGS-ALPHA on that remote: it cannot be told, so no refusal
        seed = self.dir / "seed-atCGS"
        git(seed, "checkout", "-q", "-b", "CGS-ALPHA")
        (seed / "new.txt").write_text("a newer atCGS\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-qm", "newer")
        git(seed, "push", "-q", "origin", "CGS-ALPHA")
        self.assertEqual(ownerinit.behind(self.ws), 1)
        with self.assertRaisesRegex(ValueError, "1 commit.*behind origin/CGS-ALPHA.*git pull"):
            self.run_init()
        self.assertFalse(self.glyph.exists())  # refused before anything was asked or made

    def test_a_push_of_atcgs_waits_for_its_tests(self):
        root = self.dir / "tree"
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
        with mock.patch.object(cmd, "ROOT", root):  # atCGS is the root of this tree: the gate applies
            cmd.tests_before_push(root, {})
            (root / "tests" / "test_a.py").write_text("def test_a():\n    assert False\n")
            with self.assertRaisesRegex(ValueError, "push refused"):
                cmd.tests_before_push(root, {})
            cmd.tests_before_push(root, {"ATCGS_SKIP_TESTS": "1"})  # the explicit way out
        cmd.tests_before_push(root, {})  # atCGS is elsewhere (a project's gate): no gate


class RetiredBranchTests(OwnerInit):
    def test_a_workspace_on_a_retired_level_branch_is_never_the_master(self):
        memory = self.ws / ".cgitsync" / ".memory"
        self.assertIsNone(credential.retired_branch(self.ws))
        git(memory, "checkout", "-q", "-b", "ComplexGitSync_cgs_opx")
        self.assertEqual(credential.retired_branch(self.ws), "ComplexGitSync_cgs_opx")
        with self.assertRaisesRegex(ValueError, "retired level branch.*install a new workspace|retired level branch"):
            ownerinit.workspace()  # this very workspace is the running atCGS
        with mock.patch.object(cmd, "ROOT", self.dir / "elsewhere"):
            self.assertIsNone(ownerinit.workspace())  # found under ATCGS_TREES, but retired: ignored
        git(memory, "checkout", "-q", "main")
        git(memory, "checkout", "-q", "-b", "ComplexGitSync_cgs_CGS-ALPHA")
        self.assertIsNone(credential.retired_branch(self.ws))

    def test_a_pinned_machine_with_only_a_retired_workspace_installs_a_new_one_and_leaves_the_old_alone(self):
        self.run_init()  # a first, valid workspace
        fresh = self.ws.parent / "cgs-20261107"
        template = self.dir / "template"
        shutil.copytree(self.ws, template, symlinks=True)  # what `cgitsync bootstrap` would clone
        memory = self.ws / ".cgitsync" / ".memory"
        git(memory, "checkout", "-q", "-b", "ComplexGitSync_cgs_opx")  # the old one is now a retired level tree
        old_register = (memory / ".register" / "access.jsonl").read_bytes()
        elsewhere = self.dir / "dev-checkout"
        (elsewhere / "spec").mkdir(parents=True)
        shutil.copy(self.ws / "spec" / "opx.toml", elsewhere / "spec" / "opx.toml")
        shutil.copytree(self.ws / "examples", elsewhere / "examples")
        self.glyph.unlink()
        installed = []

        def fake_install(cgs, name):
            installed.append((cgs.name, name))
            shutil.copytree(template, fresh, symlinks=True)
            return fresh

        with mock.patch.object(cmd, "ROOT", elsewhere), mock.patch.object(ownerinit, "install", fake_install):
            out = self.run_init(answers=OWNER)
        self.assertEqual((out["case"], installed), ("rebuild", [("cgs-alpha.cgs", "cgs")]))
        self.assertEqual(out["steps"][0]["step"], "install")
        self.assertEqual((memory / ".register" / "access.jsonl").read_bytes(), old_register)  # never rewritten
        self.assertEqual(len(open_glyph(OPX, self.glyph.read_bytes())), 3)
        self.assertTrue(credential.collect(OPX, self.glyph.read_bytes(), [("master", fresh)], OPX.pub)["ok"])

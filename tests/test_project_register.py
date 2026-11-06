"""MolonariCgsMolo: a read-only atCGS serves the register of the project that mounts it.

Identity is global (the master register publishes it to .omniscience, projects copy it); access is
local (each project's own grants). The master register is the one of the tree where atCGS is the root.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import atcgs.commands as cmd
from atcgs import Authorization, Unauthorized
from atcgs.identity import derive
from atcgs.journal import JournalError, Register
from atcgs.session import AccessRefused

OPX = derive("opx", "opx passphrase", profile="test")
ALICE = derive("alice", "alice passphrase", profile="test")
BOB = derive("bob", "bob passphrase", profile="test")
AUTH = Authorization(frozenset({"OPX"}))


def enrolled(directory: Path, *users) -> Register:
    reg = Register(directory, OPX.pub)
    reg.init(OPX)
    for user in users:
        reg.enrol(OPX, user.pub, user.sign(cmd.enrol_statement(user.pub)))
    return reg


class Project(unittest.TestCase):
    """<dir>/project is a MOLONARI-like tree holding a read-only atCGS at <dir>/project/.atcgs."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-proj-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.project = self.dir / "project"
        self.atcgs = self.project / ".atcgs"
        (self.project / ".cgitsync" / ".memory").mkdir(parents=True)
        self.atcgs.mkdir()
        self.published = self.dir / "published.jsonl"
        self.env = {
            "ATCGS_KDF_PROFILE": "test", "ATCGS_OPX_PUB": base64.b64encode(OPX.pub).decode(),
            "ATCGS_GLYPHS": str(self.dir / "glyphs"), "ATCGS_IDENTITIES": str(self.published),
        }
        for name in ("ATCGS_REGISTER", "CGSHOME"):
            self.env[name] = ""
        patch = mock.patch.dict(os.environ, self.env)
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("ATCGS_REGISTER", "CGSHOME"):
            os.environ.pop(name)
        root = mock.patch.object(cmd, "ROOT", self.atcgs)
        root.start()
        self.addCleanup(root.stop)

    def master(self, *users) -> Register:
        reg = enrolled(self.dir / "master", *users)
        shutil.copy(reg.identity.path, self.published)
        return reg

    def project_register(self) -> Register:
        return cmd.register()


class ProjectRootTests(Project):
    def test_a_mounted_atcgs_serves_the_enclosing_project(self):
        self.assertEqual(cmd.project_root(), self.project)
        self.assertFalse(cmd.is_master())
        self.assertEqual(cmd.register().directory, self.project / ".cgitsync" / ".memory" / ".register")

    def test_an_atcgs_that_holds_the_tree_is_the_master(self):
        (self.atcgs / ".cgitsync").mkdir()
        self.assertEqual(cmd.project_root(), self.atcgs)
        self.assertTrue(cmd.is_master())

    def test_the_explicit_register_is_a_master(self):
        with mock.patch.dict(os.environ, {"ATCGS_REGISTER": str(self.dir / "r")}):
            self.assertTrue(cmd.is_master())


class SyncTests(Project):
    def test_identities_are_copied_verbatim_and_once(self):
        self.master(ALICE)
        reg = self.project_register()
        self.assertEqual(cmd.sync_identities(reg), 2)
        self.assertEqual(reg.identity.path.read_bytes(), self.published.read_bytes())
        self.assertEqual(cmd.sync_identities(reg), 0)
        self.assertTrue(reg.state().is_active(ALICE.uid))

    def test_a_later_line_is_appended(self):
        master = self.master()
        reg = self.project_register()
        self.assertEqual(cmd.sync_identities(reg), 1)
        master.enrol(OPX, BOB.pub, BOB.sign(cmd.enrol_statement(BOB.pub)))
        shutil.copy(master.identity.path, self.published)
        self.assertEqual(cmd.sync_identities(reg), 1)
        self.assertTrue(reg.state().is_active(BOB.uid))

    def test_a_revocation_reaches_the_project(self):
        master = self.master(ALICE)
        reg = self.project_register()
        cmd.sync_identities(reg)
        master.revoke_identity(OPX, ALICE.uid, "left")
        shutil.copy(master.identity.path, self.published)
        cmd.sync_identities(reg)
        self.assertFalse(reg.state().is_active(ALICE.uid))

    def test_a_tampered_published_copy_is_refused(self):
        self.master(ALICE)
        text = self.published.read_text().replace('"seq":2', '"seq":3')
        self.published.write_text(text)
        with self.assertRaises(JournalError):
            cmd.sync_identities(self.project_register())

    def test_a_published_copy_signed_by_another_root_is_refused(self):
        enrolled_by_other = enrolled(self.dir / "other", ALICE)
        other = derive("other", "other passphrase", profile="test")
        self.assertNotEqual(other.pub, OPX.pub)
        Register(self.dir / "fake", other.pub).init(other)
        shutil.copy(self.dir / "fake" / "identity.jsonl", self.published)
        with self.assertRaises(JournalError):
            cmd.sync_identities(self.project_register())
        self.assertTrue(enrolled_by_other.state().is_active(ALICE.uid))

    def test_a_project_that_went_its_own_way_is_refused_not_merged(self):
        self.master()
        reg = self.project_register()
        enrolled(reg.directory, ALICE)  # a project-local enrol the published history never had
        enrolled(self.dir / "m2", BOB)
        shutil.copy(self.dir / "m2" / "identity.jsonl", self.published)
        with self.assertRaises(JournalError):
            cmd.sync_identities(reg)

    def test_the_master_has_nothing_to_copy(self):
        with mock.patch.dict(os.environ, {"ATCGS_REGISTER": str(self.dir / "r")}):
            self.assertEqual(cmd.sync_identities(Register(self.dir / "r", OPX.pub)), 0)


class GateTests(Project):
    def answers(self, *answers):
        return mock.patch.object(cmd, "ask", side_effect=list(answers))

    def test_a_project_register_never_revokes_an_identity_or_publishes(self):
        self.master(ALICE)
        for call in (lambda: cmd.revoke(AUTH, (ALICE.uid,)),
                     lambda: cmd.publish(AUTH)):
            with self.subTest(call=call), self.answers("opx", "opx passphrase", "opx passphrase"), \
                    self.assertRaises(Unauthorized):
                call()

    def test_admit_grants_a_known_identity_in_the_project_only(self):
        master = self.master(ALICE)
        request = self.dir / "req.json"
        key = cmd.SshKey.generate("github:flipoyo/MOLONARI1D", "DEV")
        request.write_text(json.dumps({
            "uid": ALICE.uid, "pub": base64.b64encode(ALICE.pub).decode(), "proof": "",
            "keys": [{"repo": key.repo, "role": "DEV", "ssh": key.public}]}))
        with self.answers("opx", "opx passphrase"):
            out = cmd.admit(AUTH, (str(request),))
        self.assertEqual(out["granted"][0]["repo"], "github:flipoyo/MOLONARI1D")
        self.assertEqual(self.project_register().state().roles(ALICE.uid)["github:flipoyo/MOLONARI1D"].role, "DEV")
        self.assertEqual(master.access.entries(), [])  # the master register learned nothing

    def test_admit_refuses_an_identity_the_master_does_not_know(self):
        self.master()
        request = self.dir / "req.json"
        key = cmd.SshKey.generate("github:flipoyo/MOLONARI1D", "DEV")
        request.write_text(json.dumps({
            "uid": BOB.uid, "pub": base64.b64encode(BOB.pub).decode(),
            "proof": base64.b64encode(BOB.sign(cmd.enrol_statement(BOB.pub))).decode(),
            "keys": [{"repo": key.repo, "role": "DEV", "ssh": key.public}]}))
        with self.answers("opx", "opx passphrase"), self.assertRaises(Unauthorized):
            cmd.admit(AUTH, (str(request),))
        self.assertFalse(self.project_register().state().known(BOB.uid))

    def test_login_refuses_another_tree_than_the_register_ruling(self):
        self.master(ALICE)
        elsewhere = self.dir / "elsewhere"
        elsewhere.mkdir()
        with mock.patch.dict(os.environ, {"CGSHOME": str(elsewhere)}), self.assertRaises(AccessRefused):
            cmd.login("DEV", ("MOLONARI", "status"))

    def test_login_accepts_cgshome_of_its_own_project(self):
        self.master(ALICE)
        with mock.patch.dict(os.environ, {"CGSHOME": str(self.project)}), \
                self.answers("alice", "alice passphrase"), self.assertRaises(AccessRefused) as caught:
            cmd.login("DEV", ("MOLONARI", "status"))
        self.assertIn("no GLYPH", str(caught.exception))  # past the CGSHOME check

    @unittest.skipUnless(shutil.which("ssh-agent") and shutil.which("ssh-add"), "needs ssh-agent")
    def test_a_bare_login_writes_where_it_was_typed_never_into_atcgs(self):
        self.master(ALICE)
        key = cmd.SshKey.generate("github:flipoyo/MOLONARI1D", "DEV")
        glyph = cmd.glyph_path(ALICE.uid)
        glyph.parent.mkdir(parents=True)
        glyph.write_bytes(cmd.reseal(ALICE, None, [key]))
        reg = self.project_register()
        cmd.sync_identities(reg)
        reg.grant(OPX, ALICE.uid, key.repo, "DEV", key.public)
        with mock.patch.dict(os.environ, {"INIT_CWD": str(self.atcgs)}), \
                self.answers("alice", "alice passphrase"), self.assertRaises(ValueError):
            cmd.login("DEV", ("MOLONARI",))
        self.assertFalse((self.atcgs / "MOLONARI.cgs").exists())
        typed = self.dir / "typed"
        typed.mkdir()
        with mock.patch.dict(os.environ, {"INIT_CWD": str(typed)}), self.answers("alice", "alice passphrase"):
            out = cmd.login("DEV", ("MOLONARI",))
        self.assertEqual(out["cgs"], str(typed / "MOLONARI.cgs"))
        self.assertNotIn("repos", out)


def git(cwd: Path, *argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    return done.stdout.strip()


@unittest.skipUnless(shutil.which("git") and shutil.which("ssh-agent") and shutil.which("ssh-add"), "needs git and ssh-agent")
class PublishTests(unittest.TestCase):
    """OPX publishes the identities to branch CGS-MOLO of .omniscience from a throwaway worktree."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-pub-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.remote = self.dir / "omniscience.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = self.dir / "seed"
        git(self.dir, "clone", "-q", str(self.remote), str(seed))
        (seed / "README.md").write_text("omniscience\n")
        git(seed, "add", "README.md")
        git(seed, "commit", "-qm", "init")
        git(seed, "push", "-q", "origin", "HEAD:main")
        self.root = self.dir / "cgs"
        (self.root / ".cgitsync" / ".memory").mkdir(parents=True)
        git(self.root, "clone", "-q", str(self.remote), ".omniscience")
        self.url = "https://example.test/flipoyo/omniscience.git"  # what the register may name
        git(self.root / ".omniscience", "config", f"url.file://{self.remote}.insteadOf", self.url)
        git(self.root / ".omniscience", "remote", "set-url", "origin", self.url)
        self.env = {
            "ATCGS_KDF_PROFILE": "test", "ATCGS_OPX_PUB": base64.b64encode(OPX.pub).decode(),
            "ATCGS_GLYPHS": str(self.dir / "glyphs"), "ATCGS_REGISTER": str(self.dir / "register"),
        }
        patch = mock.patch.dict(os.environ, self.env)
        patch.start()
        self.addCleanup(patch.stop)
        root = mock.patch.object(cmd, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)
        self.reg = enrolled(self.dir / "register")
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase", "opx passphrase"]):
            cmd.request("OPX", (str(self.dir / "req.json"), self.url, "OPX"))
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            cmd.admit(AUTH, (str(self.dir / "req.json"),))

    def publish(self):
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            return cmd.publish(AUTH)

    def test_publish_writes_branch_cgs_molo_and_leaves_the_checkout_alone(self):
        before = git(self.root / ".omniscience", "rev-parse", "--abbrev-ref", "HEAD")
        out = self.publish()
        self.assertEqual((out["published"], out["branch"]), (True, "CGS-MOLO"))
        shown = git(self.remote, "show", "CGS-MOLO:atcgs/identity.jsonl")
        self.assertEqual(shown + "\n", self.reg.identity.path.read_text())
        self.assertEqual(git(self.remote, "show", "CGS-MOLO:atcgs/identity.head"), out["head"])
        self.assertEqual(git(self.remote, "show", "CGS-MOLO:README.md"), "omniscience")  # from main
        self.assertEqual(git(self.root / ".omniscience", "rev-parse", "--abbrev-ref", "HEAD"), before)
        self.assertEqual(git(self.root / ".omniscience", "status", "--short"), "")
        self.assertEqual(git(self.root / ".omniscience", "worktree", "list").count("\n"), 0)

    def test_publishing_twice_changes_nothing(self):
        self.publish()
        tip = git(self.remote, "rev-parse", "CGS-MOLO")
        out = self.publish()
        self.assertEqual(out["published"], False)
        self.assertEqual(git(self.remote, "rev-parse", "CGS-MOLO"), tip)

    def test_a_new_identity_is_a_new_commit(self):
        self.publish()
        tip = git(self.remote, "rev-parse", "CGS-MOLO")
        self.reg.enrol(OPX, ALICE.pub, ALICE.sign(cmd.enrol_statement(ALICE.pub)))
        self.assertEqual(self.publish()["lines"], 2)
        self.assertEqual(git(self.remote, "rev-parse", "CGS-MOLO~1"), tip)

    def test_nothing_but_identities_is_published(self):
        self.publish()
        files = git(self.remote, "ls-tree", "-r", "--name-only", "CGS-MOLO").split()
        self.assertEqual(sorted(files), ["README.md", "atcgs/identity.head", "atcgs/identity.jsonl"])

    def test_an_opx_without_a_grant_on_omniscience_is_refused(self):
        other = self.dir / "other.git"
        git(self.dir, "clone", "-q", "--bare", str(self.remote), str(other))
        git(self.root / ".omniscience", "remote", "set-url", "origin", "https://example.test/flipoyo/other.git")
        git(self.root / ".omniscience", "config", f"url.file://{other}.insteadOf", "https://example.test/flipoyo/other.git")
        with self.assertRaises(AccessRefused):
            self.publish()


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(shutil.which("git") and shutil.which("ssh-agent") and shutil.which("ssh-add"), "needs git and ssh-agent")
class PromoteTests(unittest.TestCase):
    """`@cgs OPX login TWIN promote DIR FROM TO`: one repository, fast-forward only, through the session."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-promote-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.root = self.dir / "tree"
        (self.root / ".cgitsync" / ".memory").mkdir(parents=True)
        self.remote = self.dir / "lib.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(self.remote))
        self.url = "https://example.test/flipoyo/lib.git"
        self.repo = self.root / "lib"
        git(self.dir, "clone", "-q", str(self.remote), str(self.repo))
        git(self.repo, "config", f"url.file://{self.remote}.insteadOf", self.url)
        git(self.repo, "remote", "set-url", "origin", self.url)
        (self.repo / "a").write_text("a\n")
        git(self.repo, "add", "a")
        git(self.repo, "commit", "-qm", "a")
        git(self.repo, "push", "-q", "origin", "HEAD:main")
        git(self.repo, "checkout", "-qb", "dev")
        (self.repo / "b").write_text("b\n")
        git(self.repo, "add", "b")
        git(self.repo, "commit", "-qm", "b")
        git(self.repo, "push", "-q", "origin", "dev")
        env = {"ATCGS_KDF_PROFILE": "test", "ATCGS_OPX_PUB": base64.b64encode(OPX.pub).decode(),
               "ATCGS_GLYPHS": str(self.dir / "glyphs"), "ATCGS_REGISTER": str(self.dir / "register")}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop("CGSHOME", None)
        root = mock.patch.object(cmd, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)
        enrolled(self.dir / "register")
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase", "opx passphrase"]):
            cmd.request("OPX", (str(self.dir / "req.json"), self.url, "OPX"))
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            cmd.admit(AUTH, (str(self.dir / "req.json"),))

    def promote(self, *args):
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            return cmd.login("OPX", ("t", "promote", *args))

    def test_a_fast_forward_is_pushed(self):
        dev = git(self.remote, "rev-parse", "dev")
        out = self.promote("lib", "dev", "main")["promote"]
        self.assertEqual((out["pushed"], out["commits"], out["to"]), (True, 1, "main"))
        self.assertEqual(git(self.remote, "rev-parse", "main"), dev)
        self.assertEqual(git(self.repo, "branch", "--show-current"), "dev")  # the checkout did not move

    def test_the_local_target_branch_follows(self):
        self.promote("lib", "dev", "main")
        self.assertEqual(git(self.repo, "rev-parse", "main"), git(self.remote, "rev-parse", "dev"))

    def test_twice_is_already_up_to_date(self):
        self.promote("lib", "dev", "main")
        self.assertFalse(self.promote("lib", "dev", "main")["promote"]["pushed"])

    def test_anything_but_a_fast_forward_is_refused_and_nothing_pushed(self):
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "c").write_text("c\n")
        git(self.repo, "add", "c")
        git(self.repo, "commit", "-qm", "c")
        git(self.repo, "push", "-q", "origin", "main")
        before = git(self.remote, "rev-parse", "main")
        with self.assertRaises(ValueError):
            self.promote("lib", "dev", "main")
        self.assertEqual(git(self.remote, "rev-parse", "main"), before)

    def test_a_repository_outside_the_tree_or_ungranted_is_refused(self):
        with self.assertRaises(ValueError):
            self.promote("..", "dev", "main")
        git(self.repo, "remote", "set-url", "origin", "https://example.test/flipoyo/other.git")
        with self.assertRaises(AccessRefused):
            self.promote("lib", "dev", "main")

    def test_promote_is_an_opx_verb_only(self):
        from atcgs import _identity_request
        self.assertTrue(_identity_request("OPX", ["login", "t", "promote", "lib", "dev", "main"]))
        for layer in ("DEV", "USR"):
            self.assertFalse(_identity_request(layer, ["login", "t", "promote", "lib", "dev", "main"]))


class EnrolTests(Project):
    """`OPX enrol REQUEST`: the identity only, in the master; the twin's register gets the grants."""

    def request(self, user, repo="github:flipoyo/MOLONARI-hardware"):
        key = cmd.SshKey.generate(repo, "DEV")
        path = self.dir / f"{user.uid[:8]}.json"
        path.write_text(json.dumps({
            "uid": user.uid, "pub": base64.b64encode(user.pub).decode(),
            "proof": base64.b64encode(user.sign(cmd.enrol_statement(user.pub))).decode(),
            "keys": [{"repo": key.repo, "role": "DEV", "ssh": key.public}]}))
        return path

    def test_enrol_writes_the_identity_and_no_grant(self):
        master = enrolled(self.dir / "master")
        path = self.request(ALICE)
        with mock.patch.dict(os.environ, {"ATCGS_REGISTER": str(master.directory)}), \
                mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            out = cmd.enrol(AUTH, (str(path),))
        self.assertTrue(out["enrolled"])
        self.assertTrue(master.state().is_active(ALICE.uid))
        self.assertEqual(master.access.entries(), [])

    def test_then_the_twin_admits_the_grants_only(self):
        master = enrolled(self.dir / "master")
        path = self.request(ALICE)
        with mock.patch.dict(os.environ, {"ATCGS_REGISTER": str(master.directory)}), \
                mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            cmd.enrol(AUTH, (str(path),))
        shutil.copy(master.identity.path, self.published)  # what OPX publish does
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            cmd.admit(AUTH, (str(path),))
        twin = self.project_register().state()
        self.assertEqual(twin.roles(ALICE.uid)["github:flipoyo/MOLONARI-hardware"].role, "DEV")
        self.assertEqual(master.access.entries(), [])

    def test_enrol_twice_changes_nothing_and_a_twin_never_enrols(self):
        master = enrolled(self.dir / "master", ALICE)
        with mock.patch.dict(os.environ, {"ATCGS_REGISTER": str(master.directory)}), \
                mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            self.assertFalse(cmd.enrol(AUTH, (str(self.request(ALICE)),))["enrolled"])
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]), self.assertRaises(Unauthorized):
            cmd.enrol(AUTH, (str(self.request(BOB)),))


@unittest.skipUnless(shutil.which("ssh-agent") and shutil.which("ssh-add"), "needs ssh-agent")
class ReadGrantTests(unittest.TestCase):
    """A DEV session also loads the UID's USR grants: it reads a twin's gate, it never writes it."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-reads-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.reg = enrolled(self.dir / "register", ALICE)
        self.keys = [cmd.SshKey.generate("github:flipoyo/MOLONARI-hardware", "DEV"),
                     cmd.SshKey.generate("github:flipoyo/atCGS", "USR")]
        for key in self.keys:
            self.reg.grant(OPX, ALICE.uid, key.repo, key.role, key.public)
        self.glyph = cmd.reseal(ALICE, None, self.keys)

    def session(self, layer):
        from atcgs.session import Session
        return Session(ALICE, self.reg, self.glyph, "MOLO-HRDW", layer)

    def test_a_dev_session_holds_its_dev_and_usr_keys(self):
        with self.session("DEV") as s:
            self.assertEqual({r: g.role for r, g in s.grants.items()},
                             {"github:flipoyo/MOLONARI-hardware": "DEV", "github:flipoyo/atCGS": "USR"})
            self.assertEqual(len(s.loaded()), 2)

    def test_a_usr_session_holds_only_usr_keys(self):
        with self.session("USR") as s:
            self.assertEqual(set(s.grants), {"github:flipoyo/atCGS"})

    def test_usr_grants_alone_do_not_open_a_dev_session(self):
        reg = enrolled(self.dir / "r2", BOB)
        key = cmd.SshKey.generate("github:flipoyo/atCGS", "USR")
        reg.grant(OPX, BOB.uid, key.repo, "USR", key.public)
        from atcgs.session import Session
        with self.assertRaises(AccessRefused), Session(BOB, reg, cmd.reseal(BOB, None, [key]), "t", "DEV"):
            pass


class RefusalMessageTests(unittest.TestCase):
    def test_a_forbidden_login_operation_is_named_with_what_the_profile_may_run(self):
        from atcgs import OpFrontier
        with self.assertRaises(ValueError) as caught:
            OpFrontier().accept(["DEV", "login", "MOLO-HRDW", "tag", "v1"])
        self.assertIn("DEV may not run 'tag'", str(caught.exception))
        self.assertIn("commit", str(caught.exception))

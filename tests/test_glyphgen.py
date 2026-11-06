"""GlyphGen: a lost GLYPH is replaced (never recovered), the registers and GitHub follow; or a copy is taken back."""

import json
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

import atcgs.commands as cmd
from atcgs import OpFrontier, credential, glyphgen
from atcgs.glyph import GlyphError, open_glyph, seal
from atcgs.journal import Register, fingerprint
from tests.test_onboard import BOB, REPO, URL, Setup, git
from tests.test_project_register import OPX


class GlyphGenTests(Setup):
    def setUp(self):
        super().setUp()
        # the master workspace's memory is a git repository too, as in a real workspace
        memory = self.ws / ".cgitsync" / ".memory"
        remote = self.dir / "mastermem.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(remote))
        git(memory, "init", "-q", "-b", "main")
        git(memory, "config", f"url.file://{remote}.insteadOf", URL.format(".memory"))
        git(memory, "remote", "add", "origin", URL.format(".memory"))
        git(memory, "add", ".register")
        git(memory, "commit", "-qm", "owner")
        git(memory, "push", "-q", "origin", "HEAD:main")
        self.master_remote = remote
        self.trees_args = ("--tree", str(self.ws), "--tree", str(self.tree))
        self.glyph = cmd.glyph_path(OPX.uid)
        self.old = self.install_old_deploy_keys()

    def install_old_deploy_keys(self):
        """GitHub holds the public halves of the keys the Owner is about to lose."""
        old = {}
        for path in (self.ws, self.tree):
            for repo, grant in Register(path / ".cgitsync" / ".memory" / ".register", OPX.pub).state().roles(OPX.uid).items():
                old[(repo, grant.role)] = grant.ssh
        for (repo, role), ssh in old.items():
            name = repo.split(":", 1)[1].replace("/", "__")
            with (self.gh_state / f"{name}.keys").open("a") as handle:
                handle.write(f"{ssh}\tatCGS {role} old\ttrue\n")
        return old

    def generate(self, *args, answer="y", login=("opx", "opx passphrase"), layer="OPX"):
        with mock.patch.object(cmd, "ask", side_effect=list(login)), mock.patch.object(glyphgen, "confirm", return_value=answer):
            return glyphgen.run(layer, (*args, *self.trees_args))

    def credentials(self):
        trees = [("master", self.ws), ("TEST-PROJ", self.tree)]
        return credential.collect(OPX, self.glyph.read_bytes() if self.glyph.exists() else None, trees, OPX.pub)

    def deploy_keys(self, repo):
        file = self.gh_state / (repo.split(":", 1)[1].replace("/", "__") + ".keys")
        return [line.split("\t")[0].split()[1] for line in file.read_text().splitlines()] if file.exists() else []

    def test_a_lost_glyph_is_regenerated_everywhere_with_one_password(self):
        self.glyph.unlink()
        self.assertFalse(self.credentials()["ok"])
        out = self.generate()
        self.assertTrue(out["applied"])
        report = self.credentials()
        self.assertTrue(report["ok"])
        self.assertEqual({r["verdict"] for r in report["rows"]}, {"ok"})
        self.assertEqual(len(open_glyph(OPX, self.glyph.read_bytes())), 3)
        # GitHub: the old public keys are gone, the new ones are there
        for (repo, role), ssh in self.old.items():
            self.assertNotIn(ssh.split()[1], self.deploy_keys(repo))
        keys = {repo: self.deploy_keys(repo) for repo in {r for r, _ in self.old}}
        self.assertTrue(all(len(v) == 1 for v in keys.values()) or all(v for v in keys.values()))
        # the registers were pushed (the project's and the workspace's)
        self.assertIn("generate-glyph", git(self.remotes["memory"], "log", "-1", "--format=%s", "main"))
        self.assertIn("generate-glyph", git(self.master_remote, "log", "-1", "--format=%s", "main"))
        self.assertEqual([s["step"] for s in out["steps"]].count("old-deploy-key"), len(self.old))

    def test_a_second_run_has_nothing_to_do(self):
        self.glyph.unlink()
        self.generate()
        before = self.glyph.read_bytes()
        out = self.generate()
        self.assertEqual((out["applied"], out["reason"]), (False, "nothing to regenerate"))
        self.assertEqual(self.glyph.read_bytes(), before)

    def test_keys_the_glyph_still_has_are_kept_and_only_the_missing_one_is_made(self):
        keys = open_glyph(OPX, self.glyph.read_bytes())
        kept = [k for k in keys if not k.repo.endswith(".memory")]
        self.glyph.write_bytes(seal(OPX, kept))
        out = self.generate()
        self.assertEqual([s["detail"] for s in out["steps"] if s["step"] == "rekey"], [f"{REPO.format('.memory')} OPX"])
        now = {fingerprint(k.public) for k in open_glyph(OPX, self.glyph.read_bytes())}
        self.assertTrue({fingerprint(k.public) for k in kept} <= now)
        self.assertTrue(self.credentials()["ok"])
        self.assertTrue(list(self.glyph.parent.glob("*.bak")))  # the previous GLYPH is kept aside

    def test_a_repository_gone_from_github_gets_no_key(self):
        self.glyph.unlink()
        (self.gh_state / "gone-flipoyo__.memory").write_text("")
        out = self.generate()
        rows = {r["repo"]: r["action"] for r in out["plan"]}
        self.assertTrue(rows[REPO.format(".memory")].startswith("gone from GitHub"))
        self.assertEqual(len(open_glyph(OPX, self.glyph.read_bytes())), 2)
        report = self.credentials()
        verdicts = {(r["repo"].rsplit("/", 1)[-1], r["role"]): r["verdict"] for r in report["rows"]}
        self.assertNotIn((".memory", "OPX"), verdicts)  # its grants were revoked in the register that held them
        self.assertEqual(verdicts[("omniscience", "OPX")], "ok")
        self.assertTrue(report["ok"])
        self.assertEqual([s["step"] for s in out["steps"]].count("revoke"), 1)  # only the project register held it
        pushes = {s["tree"]: s["detail"] for s in out["steps"] if s["step"] == "push"}
        self.assertTrue(pushes[self.tree.name].startswith("failed"))  # no OPX grant is left there to push with

    def test_plan_declined_and_up_to_date_change_nothing(self):
        self.glyph.unlink()
        self.assertEqual(self.generate("--plan")["reason"], "plan only")
        self.assertEqual(self.generate(answer="n")["reason"], "declined")
        self.assertFalse(self.glyph.exists())
        self.assertEqual(sorted(len(self.deploy_keys(r)) for r in {r for r, _ in self.old}), [1, 2])  # untouched
        self.assertEqual(git(self.tree / ".cgitsync" / ".memory", "status", "--short"), "")

    def test_a_glyph_this_login_cannot_open_is_never_overwritten(self):
        other = seal(BOB, [cmd.SshKey.generate(REPO.format("x"), "DEV")])
        self.glyph.write_bytes(other)
        with self.assertRaises(GlyphError):
            self.generate()
        self.assertEqual(self.glyph.read_bytes(), other)

    def test_from_takes_back_a_copy_you_still_have(self):
        safe = self.dir / "usb"
        safe.mkdir()
        shutil.copy(self.glyph, safe / "whatever.glyph")
        want = self.glyph.read_bytes()
        self.glyph.unlink()
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            out = glyphgen.run("OPX", ("--from", str(safe)))
        self.assertEqual((out["keys"], self.glyph.read_bytes()), (3, want))
        self.assertTrue(self.credentials()["ok"])

    def test_from_refuses_a_copy_that_does_not_open(self):
        (self.dir / "usb").mkdir()
        (self.dir / "usb" / "b.glyph").write_bytes(seal(BOB, []))
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]), self.assertRaises(GlyphError):
            glyphgen.run("OPX", ("--from", str(self.dir / "usb")))

    def test_anyone_else_gets_a_request_for_the_owner_who_re_grants_the_new_key(self):
        reg = Register(self.tree / ".cgitsync" / ".memory" / ".register", OPX.pub)
        reg.enrol(OPX, BOB.pub, BOB.sign(cmd.enrol_statement(BOB.pub)))
        lost = cmd.SshKey.generate(REPO.format("lib"), "DEV")  # Bob's key was in the GLYPH he lost
        reg.grant(OPX, BOB.uid, lost.repo, "DEV", lost.public)
        out_file = self.dir / "bob.json"
        with mock.patch.object(cmd, "ask", side_effect=["bob", "bob passphrase"]), \
                mock.patch.object(glyphgen, "confirm", return_value="y"):
            out = glyphgen.run("DEV", ("--tree", str(self.tree), "--out", str(out_file)))
        self.assertEqual([s["step"] for s in out["steps"]], ["glyph", "request"])
        self.assertEqual(reg.state().roles(BOB.uid)[lost.repo].ssh.split()[1], lost.public.split()[1])  # not changed yet
        doc = json.loads(out_file.read_text())
        self.assertEqual([k["repo"] for k in doc["keys"]], [REPO.format("lib")])
        with mock.patch.dict(os.environ, {"ATCGS_PROJECT": str(self.tree), "CGSHOME": str(self.tree)}):
            cmd.admit_doc(reg, OPX, doc, keys=doc["keys"])  # the Owner's `admit`
        now = reg.state().roles(BOB.uid)[lost.repo]
        self.assertEqual(now.ssh.split()[1], doc["keys"][0]["ssh"].split()[1])
        mine = open_glyph(BOB, cmd.glyph_path(BOB.uid).read_bytes())
        self.assertEqual(fingerprint(mine[0].public), now.fingerprint)

    def test_the_output_holds_no_secret(self):
        self.glyph.unlink()
        text = json.dumps(self.generate())
        for secret in ("PRIVATE KEY", "opx passphrase", "BEGIN OPENSSH"):
            self.assertNotIn(secret, text)

    def test_the_verb_and_its_flags(self):
        for layer in ("OPX", "DEV", "USR"):
            for args in ([], ["--plan"], ["--from", "x"], ["--tree", "a", "--tree", "b", "--out", "f"]):
                self.assertEqual(OpFrontier().accept([layer, "generate-glyph", *args]).args, ("generate-glyph", *args))
        for bad in (["--from"], ["--from", "--plan"], ["--plan", "--plan"], ["x"]):
            with self.assertRaises(ValueError):
                OpFrontier().accept(["OPX", "generate-glyph", *bad])


class RekeyTests(unittest.TestCase):
    def test_a_rekey_is_one_revoke_and_one_grant_or_nothing(self):
        import tempfile

        from tests.test_project_register import enrolled
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        reg = enrolled(directory, BOB)
        old, new = cmd.SshKey.generate(REPO.format("x"), "DEV"), cmd.SshKey.generate(REPO.format("x"), "DEV")
        reg.grant(OPX, BOB.uid, old.repo, "DEV", old.public)
        reg.rekey(OPX, BOB.uid, old.repo, "DEV", new.public)
        self.assertEqual(reg.state().roles(BOB.uid)[old.repo].fingerprint, fingerprint(new.public))
        self.assertEqual([e["op"] for e in reg.access.entries()], ["grant", "revoke", "grant"])
        before = reg.access.path.read_bytes()
        with self.assertRaises(ValueError):  # the key of another grant cannot be reused: nothing is written
            other = cmd.SshKey.generate(REPO.format("y"), "DEV")
            reg.grant(OPX, BOB.uid, other.repo, "DEV", other.public)
            before = reg.access.path.read_bytes()
            reg.rekey(OPX, BOB.uid, old.repo, "DEV", other.public)
        self.assertEqual(reg.access.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

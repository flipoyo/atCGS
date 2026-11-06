"""UserCredential: what atCGS knows of one identity, and whether it adds up (read only)."""

import json
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

import atcgs.commands as cmd
import atcgs.onboard as onboard
from atcgs import OpFrontier, credential
from atcgs.glyph import seal
from atcgs.session import AccessRefused
from tests.test_onboard import BOB, CHLOE, REPO, Setup
from tests.test_project_register import AUTH, OPX


class CredentialTests(Setup):
    def collect(self, glyph="owner", **kw):
        data = cmd.glyph_path(OPX.uid).read_bytes() if glyph == "owner" else glyph
        trees = [("master", self.ws), ("TEST-PROJ", self.tree)]
        return credential.collect(OPX, data, trees, OPX.pub, **kw)

    def verdicts(self, report):
        return {(r["repo"].rsplit("/", 1)[-1], r["role"]): r["verdict"] for r in report["rows"]}

    def test_everything_in_order_is_ok(self):
        report = self.collect()
        self.assertTrue(report["ok"] and report["pinned"])
        self.assertEqual(self.verdicts(report), {("omniscience", "OPX"): "ok", (".memory", "OPX"): "ok",
                                                 ("omniscience", "USR"): "ok"})
        self.assertEqual(report["glyph"]["status"], "ok")
        self.assertEqual(report["glyph"]["keys"], 3)
        self.assertEqual([r["identity"] for r in report["registers"]], ["enrolled", "enrolled"])
        self.assertEqual(next(r for r in report["rows"] if r["role"] == "USR")["granted_in"], ["TEST-PROJ"])

    def test_a_missing_glyph_leaves_every_grant_without_a_key(self):
        report = self.collect(glyph=None)
        self.assertEqual(report["glyph"]["status"], "MISSING")
        self.assertEqual(set(self.verdicts(report).values()), {"no key"})
        self.assertFalse(report["ok"])
        self.assertIn("MISSING", credential.render(report))

    def test_another_login_does_not_open_the_glyph(self):
        other = cmd.reseal(BOB, None, [cmd.SshKey.generate(REPO.format("x"), "DEV")])
        report = self.collect(glyph=other)
        self.assertTrue(report["glyph"]["status"].startswith("unreadable"))
        self.assertEqual(set(self.verdicts(report).values()), {"no key"})

    def test_a_key_that_was_never_admitted_is_an_orphan(self):
        glyph = cmd.glyph_path(OPX.uid)
        glyph.write_bytes(cmd.reseal(OPX, glyph.read_bytes(), [cmd.SshKey.generate(REPO.format("lib"), "DEV")]))
        report = self.collect()
        self.assertEqual(self.verdicts(report)[("lib", "DEV")], "not admitted")
        self.assertTrue(report["ok"])  # an orphan is reported, it does not fail the credentials

    def test_a_grant_whose_key_is_not_in_the_glyph_is_no_key(self):
        reg = credential.Register(self.tree / ".cgitsync" / ".memory" / ".register", OPX.pub)
        stranger = cmd.SshKey.generate(REPO.format("lib"), "DEV")  # granted, but never sealed in this GLYPH
        reg.grant(OPX, OPX.uid, stranger.repo, "DEV", stranger.public)
        report = self.collect()
        self.assertEqual(self.verdicts(report)[("lib", "DEV")], "no key")
        self.assertFalse(report["ok"])

    def test_a_revoked_identity_is_reported_revoked(self):
        key = cmd.SshKey.generate(REPO.format("lib"), "DEV")
        reg = credential.Register(self.tree / ".cgitsync" / ".memory" / ".register", OPX.pub)
        reg.enrol(OPX, BOB.pub, BOB.sign(cmd.enrol_statement(BOB.pub)))
        reg.grant(OPX, BOB.uid, key.repo, "DEV", key.public)
        glyph = seal(BOB, [key])
        self.assertEqual(self.verdicts(credential.collect(BOB, glyph, [("TEST-PROJ", self.tree)], OPX.pub)),
                         {("lib", "DEV"): "ok"})
        reg.revoke_identity(OPX, BOB.uid, "left")
        report = credential.collect(BOB, glyph, [("TEST-PROJ", self.tree)], OPX.pub)
        self.assertEqual(report["registers"][0]["identity"], "revoked")
        self.assertEqual(self.verdicts(report), {("lib", "DEV"): "revoked"})

    def test_an_identity_no_register_knows_has_no_grant_anywhere(self):
        report = credential.collect(BOB, None, [("TEST-PROJ", self.tree)], OPX.pub)
        self.assertEqual((report["registers"][0]["identity"], report["rows"]), ("unknown", []))

    def test_github_refusal_is_a_verdict_of_its_own(self):
        report = self.collect(probe=lambda tree, identity, glyph: {("flipoyo/omniscience", "USR")})
        self.assertEqual(self.verdicts(report)[("omniscience", "USR")], "refused by GitHub")
        self.assertEqual(self.verdicts(report)[(".memory", "OPX")], "ok")

    @unittest.skipUnless(shutil.which("ssh-agent") and shutil.which("ssh-add"), "needs ssh-agent")
    def test_the_probe_tries_each_key_through_a_session_of_its_own(self):
        seen = []

        def test(session, repo):
            seen.append((repo, sorted(session.grants)))
            return not repo.endswith("/omniscience")

        report = self.collect(probe=lambda t, i, g: credential.probe_github(
            credential._read_tree("p", t.path, i, OPX.pub), i, g, test))
        self.assertEqual({repo for repo, _ in seen}, {REPO.format(".memory"), REPO.format("omniscience")})
        self.assertEqual(self.verdicts(report)[("omniscience", "USR")], "refused by GitHub")

    def test_the_output_holds_no_secret(self):
        report = json.dumps(self.collect()) + credential.render(self.collect())
        for secret in ("PRIVATE KEY", "opx passphrase", "BEGIN OPENSSH"):
            self.assertNotIn(secret, report)

    def test_nothing_depends_on_the_working_directory(self):
        answers = lambda: mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"])  # noqa: E731
        outs = []
        for where in (self.ws, self.tree, self.dir):
            old = Path.cwd()
            os.chdir(where)
            try:
                with answers():
                    outs.append(cmd.user_credential("OPX", ("--json", "--tree", str(self.ws), "--tree", str(self.tree))))
            finally:
                os.chdir(old)
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[1], outs[2])
        self.assertEqual(outs[0]["__exit__"], 0)

    def test_exit_status_tells_whether_the_credentials_are_in_order(self):
        cmd.glyph_path(OPX.uid).unlink()
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]):
            out = cmd.user_credential("OPX", ("--tree", str(self.tree)))
        self.assertEqual(out["__exit__"], 1)
        self.assertIn("MISSING", out["__text__"])

    def test_discover_lists_the_master_before_the_projects(self):
        base = self.dir / "home"
        for name, master in (("cgs-1", True), ("PROJ-2", False)):
            (base / name / ".cgitsync" / ".memory" / ".register").mkdir(parents=True)
            if master:
                (base / name / "atcgs").mkdir()
                (base / name / "atcgs" / "__init__.py").write_text("")
        self.assertEqual([label for label, _ in credential.discover(base)], ["master cgs-1", "PROJ"])

    def test_the_verb_is_accepted_at_every_level_with_known_flags_only(self):
        for layer in ("OPX", "DEV", "USR"):
            for args in ([], ["--json"], ["--probe", "--json"], ["--tree", "p", "--tree", "q"]):
                self.assertEqual(OpFrontier().accept([layer, "user-credential", *args]).args, ("user-credential", *args))
        for bad in (["--tree"], ["--tree", "--json"], ["--wat"], ["x"]):
            with self.assertRaises(ValueError):
                OpFrontier().accept(["OPX", "user-credential", *bad])
        with self.assertRaises(ValueError):
            OpFrontier().accept(["PUB", "user-credential"])


class OwnerFirstTests(Setup):
    """`OPX onboard` verifies the Owner's own credentials before it creates anyone."""

    def listed(self):
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        self.make_registration(CHLOE, "Chloe", {"TEST-PROJ": "USR"})
        return self.build_list()

    def run_onboard(self, path):
        with mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"]), \
                mock.patch.object(onboard, "confirm", return_value="y"):
            return onboard.run(AUTH, path)

    def test_no_glyph_stops_before_anything_is_created(self):
        path = self.listed()
        cmd.glyph_path(OPX.uid).unlink()
        with self.assertRaisesRegex(AccessRefused, "user-credential"):
            self.run_onboard(path)
        self.assertFalse(credential.Register(self.ws / ".cgitsync" / ".memory" / ".register", OPX.pub)
                         .state().known(BOB.uid))

    def test_a_grant_without_its_key_stops_the_run(self):
        path = self.listed()
        glyph = cmd.glyph_path(OPX.uid)
        keys = [k for k in credential.open_glyph(OPX, glyph.read_bytes()) if k.role != "USR"]  # drop project-omni
        glyph.write_bytes(seal(OPX, keys))
        with self.assertRaisesRegex(AccessRefused, "omniscience USR: no key"):
            self.run_onboard(path)
        self.assertFalse(credential.Register(self.ws / ".cgitsync" / ".memory" / ".register", OPX.pub)
                         .state().known(BOB.uid))

    def test_in_order_the_run_goes_through(self):
        self.assertEqual(self.run_onboard(self.listed())["failed"], [])


if __name__ == "__main__":
    unittest.main()

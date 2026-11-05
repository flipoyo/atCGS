"""IdentityJournals M1-M4: identity key, journals, GLYPH, session and @cgs verbs (README § 3)."""

import base64
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from atcgs import OpFrontier, run
from atcgs import commands as cmd
from atcgs.glyph import GLYPH_BYTES, GlyphError, SshKey, open_glyph, reseal, seal, to_pbm
from atcgs.identity import Identity, derive
from atcgs.journal import JournalError, Register, enrol_statement, fingerprint
from atcgs.session import AccessRefused, Session

REPO, OTHER = "github:flipoyo/demo", "github:flipoyo/other"
HAS_AGENT = bool(shutil.which("ssh-agent") and shutil.which("ssh-add"))


def ident(login: str, password: str | None = None) -> Identity:
    return derive(login, password or f"{login} passphrase", profile="test")


OPX, ALICE, BOB = ident("opx"), ident("alice"), ident("bob")


class Lab(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-test-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.reg = Register(self.dir / "register", OPX.pub)
        self.reg.init(OPX)

    def enrol(self, who: Identity) -> None:
        self.reg.enrol(OPX, who.pub, who.sign(enrol_statement(who.pub)))

    def grant(self, who: Identity, repo: str = REPO, role: str = "DEV") -> SshKey:
        key = SshKey.generate(repo, role)
        self.reg.grant(OPX, who.uid, repo, role, key.public)
        return key


class IdentityTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(ident("alice").pub, ALICE.pub)

    def test_one_character_changes_the_uid(self):
        uids = {ALICE.uid, ident("alicf", "alice passphrase").uid, ident("alice", "alice passphrasf").uid}
        self.assertEqual(len(uids), 3)

    def test_profile_is_in_the_salt(self):
        self.assertNotEqual(derive("a", "b", profile="test").uid, derive("a", "b", profile="real").uid)

    def test_no_secret_in_repr(self):
        secret = derive("carol", "s3cret-passphrase", profile="test")
        self.assertNotIn("s3cret", repr(secret))
        self.assertNotIn(secret._seed.hex(), repr(secret))

    def test_empty_inputs_refused(self):
        for login, password in (("", "x"), ("x", "")):
            with self.subTest(login=login), self.assertRaises(ValueError):
                derive(login, password, profile="test")


class JournalTests(Lab):
    def test_enrol_grant_role(self):
        self.enrol(ALICE)
        key = self.grant(ALICE)
        state = self.reg.state()
        self.assertEqual(state.role(ALICE.uid, REPO), "DEV")
        self.assertEqual(state.role(ALICE.uid, OTHER), "PUB")
        self.assertEqual(state.roles(ALICE.uid)[REPO].fingerprint, fingerprint(key.public))

    def test_journal_opens_with_the_pinned_opx(self):
        other = Register(self.dir / "other", OPX.pub)
        with self.assertRaises(JournalError):
            other.enrol(OPX, ALICE.pub, ALICE.sign(enrol_statement(ALICE.pub)))
        with self.assertRaises(JournalError):
            Register(self.dir / "third", OPX.pub).init(ALICE)

    def test_enrol_needs_proof_of_possession(self):
        with self.assertRaises(JournalError):
            self.reg.enrol(OPX, ALICE.pub, BOB.sign(enrol_statement(ALICE.pub)))

    def test_enrol_needs_opx(self):
        self.enrol(BOB)
        with self.assertRaises(JournalError):
            self.reg.enrol(BOB, ALICE.pub, ALICE.sign(enrol_statement(ALICE.pub)))

    def tampered(self, path: Path, edit) -> None:
        lines = path.read_text().splitlines()
        path.write_text("\n".join(edit(lines)) + "\n")
        with self.assertRaises(JournalError):
            self.reg.state()

    def test_tamper_reorder_delete_replay(self):
        self.enrol(ALICE)
        self.enrol(BOB)
        path = self.reg.identity.path
        original = path.read_text()
        cases = {
            "tamper": lambda ls: [ls[0], ls[1].replace('"enrol"', '"rotate"'), ls[2]],
            "reorder": lambda ls: [ls[0], ls[2], ls[1]],
            "delete": lambda ls: [ls[0], ls[2]],
            "replay": lambda ls: [*ls, ls[1]],
            "garbage": lambda ls: [*ls, "not json"],
        }
        for name, edit in cases.items():
            with self.subTest(case=name):
                self.tampered(path, edit)
                path.write_text(original)
        self.reg.state()

    def test_grant_signed_by_someone_else_refuses_the_file(self):
        self.enrol(ALICE)
        entries = self.reg.access.entries()
        body = {"repo": REPO, "role": "OPX", "ssh": SshKey.generate(REPO, "OPX").public}
        entries.append(self.reg.access.draft(entries, "grant", ALICE.uid, body, ALICE))
        self.reg.access.write(entries)
        with self.assertRaises(JournalError):
            self.reg.state()

    def test_revoked_uid_loses_its_grants_and_cannot_be_granted(self):
        self.enrol(ALICE)
        self.grant(ALICE)
        self.reg.revoke_identity(OPX, ALICE.uid)
        self.assertEqual(self.reg.state().roles(ALICE.uid), {})
        with self.assertRaises(JournalError):
            self.grant(ALICE, OTHER)

    def test_self_revoke(self):
        self.enrol(ALICE)
        self.reg.revoke_identity(ALICE, ALICE.uid, "lost laptop")
        self.assertFalse(self.reg.state().is_active(ALICE.uid))
        with self.assertRaises(JournalError):
            self.reg.revoke_identity(BOB, ALICE.uid)

    def test_rotate_keeps_the_grants(self):
        self.enrol(ALICE)
        self.grant(ALICE)
        new = ident("alice", "a new passphrase")
        self.reg.rotate(ALICE, new)
        state = self.reg.state()
        self.assertFalse(state.is_active(ALICE.uid))
        self.assertEqual(state.role(new.uid, REPO), "DEV")
        self.reg.revoke_access(OPX, new.uid, REPO)
        self.assertEqual(self.reg.state().role(new.uid, REPO), "PUB")

    def test_opx_cannot_be_rotated_or_revoked(self):
        with self.assertRaises(JournalError):
            self.reg.rotate(OPX, ident("opx", "other"))
        with self.assertRaises(JournalError):
            self.reg.revoke_identity(OPX, OPX.uid)

    def test_one_role_per_repo_and_one_repo_per_key(self):
        self.enrol(ALICE)
        key = self.grant(ALICE)
        with self.assertRaises(JournalError):
            self.grant(ALICE, REPO, "USR")
        with self.assertRaises(JournalError):
            self.reg.grant(OPX, ALICE.uid, OTHER, "DEV", key.public)

    def test_no_secret_in_the_journals(self):
        self.enrol(ALICE)
        self.grant(ALICE)
        text = self.reg.identity.path.read_text() + self.reg.access.path.read_text()
        for secret in ("alice", "passphrase", "PRIVATE KEY"):
            self.assertNotIn(secret, text)


class GlyphTests(unittest.TestCase):
    def setUp(self):
        self.keys = [SshKey.generate(REPO, "DEV"), SshKey.generate(OTHER, "USR")]

    def test_round_trip_and_size(self):
        glyph = seal(ALICE, self.keys)
        self.assertEqual(len(glyph), GLYPH_BYTES)
        self.assertEqual([k.private for k in open_glyph(ALICE, glyph)], [k.private for k in self.keys])

    def test_every_single_bit_flip_is_refused(self):
        glyph = seal(ALICE, self.keys)
        for position in (0, 4, 5, 16, 17, 4000, GLYPH_BYTES - 1):
            bad = bytearray(glyph)
            bad[position] ^= 1
            with self.subTest(position=position), self.assertRaises(GlyphError):
                open_glyph(ALICE, bytes(bad))

    def test_wrong_password_refused(self):
        with self.assertRaises(GlyphError):
            open_glyph(ident("alice", "wrong"), seal(ALICE, self.keys))

    def test_fresh_nonce(self):
        self.assertNotEqual(seal(ALICE, self.keys), seal(ALICE, self.keys))

    def test_capacity(self):
        many = [SshKey.generate(f"github:o/r{i}", "DEV") for i in range(17)]
        seal(ALICE, many)
        with self.assertRaises(GlyphError):
            seal(ALICE, [*many, *(SshKey.generate(f"github:o/x{i}", "DEV") for i in range(3))])

    def test_reseal_adds(self):
        glyph = reseal(ALICE, seal(ALICE, self.keys[:1]), self.keys[1:])
        self.assertEqual(len(open_glyph(ALICE, glyph)), 2)

    def test_no_secret_in_repr_and_pbm(self):
        self.assertNotIn("PRIVATE", repr(self.keys[0]))
        pbm = to_pbm(seal(ALICE, self.keys))
        self.assertEqual((pbm[:11], len(pbm)), (b"P4\n256 256\n", 11 + GLYPH_BYTES))


@unittest.skipUnless(HAS_AGENT, "ssh-agent and ssh-add are needed")
class SessionTests(Lab):
    def setUp(self):
        super().setUp()
        self.enrol(ALICE)
        self.dev = self.grant(ALICE, REPO, "DEV")
        self.usr = self.grant(ALICE, OTHER, "USR")
        self.glyph = seal(ALICE, [self.dev, self.usr])

    def test_loads_only_the_requested_role(self):
        with Session(ALICE, self.reg, self.glyph, "demo", "DEV") as s:
            self.assertEqual(s.loaded(), [fingerprint(self.dev.public)])
            self.assertIn(REPO, s.cgs())
            self.assertNotIn(OTHER, s.cgs())
            socket = Path(s.env()["SSH_AUTH_SOCK"])
            self.assertTrue(socket.exists())
        self.assertFalse(socket.parent.exists())

    def test_agent_is_gone_after_an_exception(self):
        with self.assertRaises(RuntimeError):
            with Session(ALICE, self.reg, self.glyph, "demo", "USR") as s:
                socket = Path(s.env()["SSH_AUTH_SOCK"])
                raise RuntimeError("boom")
        self.assertFalse(socket.parent.exists())
        self.assertIsNone(s._agent)

    def test_refusals(self):
        cases = {
            "unknown": (ident("alice", "wrong"), self.glyph, "DEV", AccessRefused),
            "no grant": (ALICE, self.glyph, "OPX", AccessRefused),
            "glyph without the key": (ALICE, seal(ALICE, [self.usr]), "DEV", GlyphError),
            "altered glyph": (ALICE, bytes([self.glyph[0] ^ 1]) + self.glyph[1:], "DEV", GlyphError),
        }
        for name, (who, glyph, layer, error) in cases.items():
            with self.subTest(case=name), self.assertRaises(error):
                with Session(who, self.reg, glyph, "demo", layer):
                    pass

    def test_cgs_is_valid_for_cgitsync(self):
        from ComplexGitSync.tree.cgs_format import CgsDocument

        with Session(ALICE, self.reg, self.glyph, "demo", "DEV") as s:
            path = s.write_cgs(self.dir)
        CgsDocument.from_toml(path).validate()
        self.assertNotIn(ALICE.uid, path.read_text())

    def test_subprocess_gets_the_agent_and_no_identity(self):
        with Session(ALICE, self.reg, self.glyph, "demo", "DEV") as s:
            env = s.env({"PATH": os.environ["PATH"], "SSH_AGENT_PID": "1", "GIT_SSH": "x"})
        self.assertEqual(set(env), {"PATH", "SSH_AUTH_SOCK", "GIT_SSH_COMMAND"})

    def test_the_session_ssh_maps_each_repo_to_its_public_key_only(self):
        with Session(ALICE, self.reg, self.glyph, "demo", "USR") as s:
            wrapper = Path(s.env()["GIT_SSH_COMMAND"])
            self.assertTrue(os.access(wrapper, os.X_OK))
            self.assertIn("-F /dev/null", wrapper.read_text())
            mapping = dict(line.split() for line in (wrapper.parent / "keys.map").read_text().splitlines())
            self.assertEqual(list(mapping), ["flipoyo/other"])
            self.assertEqual(Path(mapping["flipoyo/other"]).read_text().strip(), self.usr.public)
            written = "".join(p.read_text() for p in wrapper.parent.rglob("*") if p.is_file())
            self.assertNotIn("PRIVATE KEY", written)
        self.assertFalse(wrapper.exists())

    def test_repo_path(self):
        from atcgs.session import repo_path

        for repo in ("github:flipoyo/atCGS", "https://github.com/flipoyo/atCGS.git", "github:FLIPOYO/atcgs/"):
            with self.subTest(repo=repo):
                self.assertEqual(repo_path(repo), "flipoyo/atcgs")


class DeployKeysTests(Lab):
    def test_one_gh_command_per_active_github_grant(self):
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from deploy_keys import commands

        self.enrol(ALICE)
        self.enrol(BOB)
        dev = self.grant(ALICE, REPO, "DEV")
        self.grant(BOB, REPO, "USR")
        self.grant(BOB, OTHER, "USR")
        self.reg.revoke_access(OPX, BOB.uid, OTHER)
        lines = commands(self.reg.state())
        self.assertEqual(len(lines), 2)
        mine = next(line for line in lines if dev.public in line)
        self.assertIn("repos/flipoyo/demo/keys", mine)
        self.assertIn("read_only=false", mine)
        self.assertNotIn("PRIVATE", "".join(lines))

    def test_only_the_named_repos(self):
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from deploy_keys import commands

        self.enrol(ALICE)
        self.grant(ALICE, REPO, "DEV")
        self.grant(ALICE, OTHER, "DEV")
        self.assertEqual(len(commands(self.reg.state())), 2)
        only = commands(self.reg.state(), frozenset({OTHER}))
        self.assertEqual(len(only), 1)
        self.assertIn("repos/flipoyo/other/keys", only[0])
        self.assertEqual(commands(self.reg.state(), frozenset({"github:flipoyo/absent"})), [])


class SelectorTests(unittest.TestCase):
    def test_identity_verbs(self):
        accept = OpFrontier().accept
        for argv in (["OPX", "init"], ["USR", "request", "out.json", REPO, "USR"],
                     ["OPX", "admit", "r.json"], ["OPX", "revoke", "u"], ["OPX", "revoke", "u", REPO],
                     ["DEV", "login", "demo"], ["DEV", "login", "demo", "status"],
                     ["USR", "login", "demo", "fetch"], ["DEV", "login", "demo", "commit", "-m", "x"],
                     ["DEV", "login", "demo", "push"], ["OPX", "login", "demo", "tag", "v1"],
                     ["OPX", "login", "demo", "bootstrap", "demo.cgs", "demo"]):
            with self.subTest(argv=argv):
                self.assertEqual(accept(argv).args, tuple(argv[1:]))
        for argv in (["DEV", "init"], ["DEV", "admit", "r.json"], ["PUB", "login", "demo"],
                     ["USR", "request", "out.json", REPO], ["DEV", "login", "demo", "bash"],
                     ["USR", "login", "demo", "push"], ["USR", "login", "demo", "commit"],
                     ["DEV", "login", "demo", "tag", "v1"], ["DEV", "login", "demo", "bootstrap", "x.cgs"],
                     ["USR", "revoke", "u"], ["OPX", "prove", "X", "a", "b"]):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                accept(argv)


@unittest.skipUnless(HAS_AGENT, "ssh-agent and ssh-add are needed")
class CommandTests(unittest.TestCase):
    """The verbs end to end through `run`, with scripted getpass answers."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-cli-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.env = {
            "ATCGS_KDF_PROFILE": "test", "ATCGS_REGISTER": str(self.dir / "register"),
            "ATCGS_OPX_PUB": base64.b64encode(OPX.pub).decode(), "ATCGS_GLYPHS": str(self.dir / "glyphs"),
            "ATCGS_AUTHORIZE": "OPX", "INIT_CWD": str(self.dir),
        }
        cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, cwd)

    def cgs(self, answers, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, self.env), mock.patch.object(cmd, "ask", side_effect=answers), \
                redirect_stdout(out), redirect_stderr(err):
            code = run(list(argv))
        return code, (json.loads(out.getvalue()) if out.getvalue() else None), err.getvalue()

    def test_full_cycle(self):
        opx = ["opx", "opx passphrase"]
        alice = ["alice", "alice passphrase"]
        self.assertEqual(self.cgs(opx + opx[1:], "OPX", "init")[0], 0)
        code, out, _ = self.cgs(alice + alice[1:], "DEV", "request", "req.json", REPO, "DEV")
        self.assertEqual((code, out["uid"]), (0, ALICE.uid))
        request = (self.dir / "req.json").read_text()
        for secret in ("alice passphrase", "PRIVATE KEY"):
            self.assertNotIn(secret, request)
        code, out, _ = self.cgs(opx, "OPX", "admit", "req.json")
        self.assertEqual((code, out["granted"][0]["role"]), (0, "DEV"))
        code, out, _ = self.cgs(alice, "DEV", "login", "demo")
        self.assertEqual((code, out["code"], out["agent_keys"], out["closed"]), (0, "1000", 1, True))
        self.assertTrue((self.dir / "demo.cgs").exists())
        (self.dir / "demo.cgs").unlink()
        code, out, _ = self.cgs(alice, "DEV", "login", "demo", "status")
        self.assertEqual((code, out["cgs"]), (0, None))  # inside a tree: no stray TWIN.cgs
        self.assertFalse((self.dir / "demo.cgs").exists())
        self.assertIn("cgitsync", out)
        code, _, err = self.cgs(alice, "USR", "login", "demo")
        self.assertEqual(code, 3)
        self.assertIn("no USR grant", err)
        self.assertEqual(self.cgs(opx, "OPX", "revoke", ALICE.uid)[0], 0)
        code, _, err = self.cgs(alice, "DEV", "login", "demo")
        self.assertEqual(code, 3)
        self.assertNotIn("alice passphrase", err)

    def test_init_without_a_pin_prints_the_key_to_pin(self):
        del self.env["ATCGS_OPX_PUB"]
        with mock.patch.object(cmd, "ROOT", self.dir):
            (self.dir / "spec").mkdir()
            (self.dir / "spec/contracts.toml").write_text('[identity]\nopx_pub = ""\n')
            code, out, _ = self.cgs(["opx", "opx passphrase", "opx passphrase"], "OPX", "init")
        self.assertEqual((code, out["pinned"], out["idpub"]), (0, False, base64.b64encode(OPX.pub).decode()))
        self.assertFalse((self.dir / "register").exists())

    def test_admit_needs_the_pinned_opx(self):
        self.cgs(["opx", "opx passphrase", "opx passphrase"], "OPX", "init")
        self.cgs(["bob", "bob passphrase", "bob passphrase"], "USR", "request", "req.json", REPO, "USR")
        code, _, err = self.cgs(["bob", "bob passphrase"], "OPX", "admit", "req.json")
        self.assertEqual(code, 3)
        del self.env["ATCGS_AUTHORIZE"]
        self.assertEqual(self.cgs(["opx", "opx passphrase"], "OPX", "admit", "req.json")[0], 3)

    def test_mismatched_passwords(self):
        code, _, err = self.cgs(["alice", "one", "two"], "DEV", "request", "req.json", REPO, "DEV")
        self.assertEqual(code, 2)
        self.assertNotIn("one", err.replace("one of", ""))


if __name__ == "__main__":
    unittest.main()

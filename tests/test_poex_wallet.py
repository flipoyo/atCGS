"""POEX and EOPX: the Python classes wrapping the C poex and eopx microcodes (offline)."""
import hashlib
import io
import json
import os
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from atcgs import (
    AUTHORIZE_ENV,
    EOPX,
    PIXI_ENV,
    POE_CODES,
    POEX,
    PRIME_CGS,
    REGISTER_ENV,
    ROOT,
    OpFrontier,
    Register,
    build,
    run,
)

SEED = (Path(__file__).resolve().parents[1] / "fixtures/demo_256x256.bit").read_bytes()
BIG_SEED = bytes(range(256)) * 128  # 32768 bytes = 512x512 bits


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def glyph_of(seed):
    """Reference for the birth compression, used only to check the C microcode."""
    return hashlib.shake_256(hashlib.sha256(seed).digest() + seed).digest(8192)


class Microcodes(unittest.TestCase):
    def setUp(self):
        if not shutil.which("cc") or not shutil.which("ssh-keygen"):
            self.skipTest("needs a C11 compiler and ssh-keygen")
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.opx = {}
        self.eopx = EOPX(build("eopx", Path(tmp.name)), self.opx)
        self.wallet = POEX(build("poex", Path(tmp.name)), self.eopx)
        self.sent = []

    def send(self, private, seed_id):
        self.sent.append((private, seed_id, private.exists()))
        self.dev_public = Path(f"{private}.pub").read_bytes().strip()


class EOPXTests(Microcodes):
    def test_glyph_is_the_deterministic_compression(self):
        for seed in (SEED, BIG_SEED):
            with self.subTest(size=len(seed)):
                self.assertEqual(self.eopx.glyph(seed), glyph_of(seed))
                self.assertEqual(self.eopx.glyph(seed), self.eopx.glyph(seed))

    def test_seed_must_be_square_and_at_least_256(self):
        for bad in (SEED[:-1], bytes(4096), bytes(8192 + 1)):
            with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                self.eopx.glyph(bad)

    def test_minimal_seed_is_still_compressed(self):
        self.assertNotEqual(sha256(self.eopx.glyph(SEED)), sha256(SEED))

    def test_birth_registers_the_pair_with_opx(self):
        self.eopx.birth("X", BIG_SEED)
        self.assertEqual(self.opx["X"], (sha256(BIG_SEED), sha256(glyph_of(BIG_SEED))))

    def test_hash_seed_is_a_unique_id(self):
        self.eopx.birth("X", SEED)
        with self.assertRaises(ValueError):
            self.eopx.birth("Y", SEED)
        with self.assertRaises(ValueError):
            self.eopx.birth("X", BIG_SEED)
        self.assertEqual(list(self.opx), ["X"])

    def test_bad_seed_registers_nothing(self):
        with self.assertRaises(ValueError):
            self.eopx.birth("X", SEED[:-1])
        self.assertEqual(self.opx, {})


class POEXTests(Microcodes):
    def test_compare_rebuilds_two_glyphs(self):
        self.assertTrue(self.wallet.compare(SEED, SEED))
        self.assertTrue(self.wallet.compare(BIG_SEED, BIG_SEED))
        self.assertFalse(self.wallet.compare(SEED, BIG_SEED))
        flipped = bytes([SEED[0] ^ 1]) + SEED[1:]
        self.assertFalse(self.wallet.compare(SEED, flipped))

    def test_compare_refuses_a_bad_seed(self):
        with self.assertRaises(ValueError):
            self.wallet.compare(SEED, SEED[:-1])

    def test_new_name_is_born_then_served(self):
        self.assertFalse(self.wallet.exists("X"))
        cred = self.wallet.cred("X", lambda: BIG_SEED, self.send)
        self.assertTrue(self.wallet.exists("X"))
        self.assertEqual((cred.opx, cred.usr, cred.pub),
                         (sha256(glyph_of(BIG_SEED)), sha256(b"X"), sha256(BIG_SEED)))
        self.assertEqual(len(cred.packet()), 128)
        self.assertEqual([cred.slot(layer) for layer in PRIME_CGS], [cred.opx, cred.dev, cred.usr, cred.pub])

    def test_known_name_never_asks_its_seed_again(self):
        self.wallet.cred("X", lambda: SEED, self.send)

        def refuse():
            raise AssertionError("SEED asked for a NAME that exists in PoE")

        self.assertEqual(self.wallet.cred("X", refuse, self.send).pub, sha256(SEED))

    def test_frontier_gets_hash_seed_and_a_destroyed_dev_key(self):
        cred = self.wallet.cred("X", lambda: SEED, self.send)
        private, seed_id, existed = self.sent[0]
        self.assertEqual(seed_id, sha256(SEED))
        self.assertTrue(existed)
        self.assertFalse(private.parent.exists())
        self.assertEqual(cred.dev, sha256(self.dev_public))

    def test_dev_key_destroyed_when_send_fails(self):
        seen = []

        def send(private, seed_id):
            seen.append(private)
            raise OSError("frontier unreachable")

        with self.assertRaises(OSError):
            self.wallet.cred("X", lambda: SEED, send)
        self.assertFalse(seen[0].parent.exists())

    def test_glyph_is_never_stored_nor_delivered(self):
        glyph = glyph_of(SEED)
        cred = self.wallet.cred("X", lambda: SEED, self.send)
        for held in (repr(cred), repr(self.opx), repr(self.sent), repr(self.wallet)):
            self.assertNotIn(glyph.hex(), held)
        self.assertNotIn(glyph, cred.packet())


class SessionTests(Microcodes):
    REFUSED = {"OPX": 0b1000, "DEV": 0b1100, "USR": 0b1110, "PUB": 0b1111}

    def setUp(self):
        super().setUp()
        self.eopx.birth("X", SEED)

    def test_ladder(self):
        self.assertEqual({k: format(v, "04b") for k, v in POE_CODES.items()},
                         {"POE": "0000", "OPX": "1000", "DEV": "1100", "USR": "1110", "PUB": "1111"})

    def test_granted_is_0000_for_every_requester(self):
        with self.wallet.session() as session:
            for requester in PRIME_CGS:
                with self.subTest(requester=requester):
                    self.assertEqual(session.prove("X", SEED, SEED, requester), 0b0000)
                    self.assertEqual(session.poe("X"), 0b0000)

    def test_left_differs_from_right_keeps_the_requesters_code(self):
        with self.wallet.session() as session:
            for requester, code in self.REFUSED.items():
                with self.subTest(requester=requester):
                    self.assertEqual(session.prove("X", SEED, BIG_SEED, requester), code)

    def test_failed_control_keeps_the_requesters_code(self):
        # BIG_SEED is not X's SEED: GLYPH(left) does not match OPX's hash(GLYPH).
        with self.wallet.session() as session:
            for requester, code in self.REFUSED.items():
                with self.subTest(requester=requester):
                    self.assertEqual(session.prove("X", BIG_SEED, BIG_SEED, requester), code)

    def test_only_opx_gives_birth_to_an_unknown_name(self):
        with self.wallet.session() as session:
            for requester in ("DEV", "USR", "PUB"):
                with self.subTest(requester=requester):
                    self.assertEqual(session.prove("Y", BIG_SEED, BIG_SEED, requester), self.REFUSED[requester])
                    self.assertFalse(self.wallet.exists("Y"))
            self.assertEqual(session.prove("Y", BIG_SEED, BIG_SEED, "OPX"), 0b0000)
        self.assertEqual(self.opx["Y"], (sha256(BIG_SEED), sha256(glyph_of(BIG_SEED))))

    def test_unknown_requester_is_refused(self):
        with self.wallet.session() as session, self.assertRaises(ValueError):
            session.prove("X", SEED, SEED, "ROOT")

    def test_poe_holds_only_for_the_session(self):
        session = self.wallet.session()
        session.prove("X", SEED, SEED, "DEV")
        glyph = session._glyphs["X"]
        session.close()
        self.assertEqual(bytes(glyph), bytes(8192))
        with self.assertRaises(ValueError):
            session.poe("X")
        with self.assertRaises(ValueError):
            session.prove("X", SEED, SEED, "DEV")
        with self.wallet.session() as fresh, self.assertRaises(ValueError):
            fresh.poe("X")

    def test_only_a_granted_glyph_is_decorated_and_never_shown(self):
        with self.wallet.session() as session:
            session.prove("X", SEED, BIG_SEED, "USR")
            self.assertEqual(session._glyphs, {})
            session.prove("X", SEED, SEED, "USR")
            self.assertEqual(bytes(session._glyphs["X"]), glyph_of(SEED))
            self.assertNotIn(glyph_of(SEED).hex(), repr(session))


class RegisterTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "register" / "opx.json"

    def test_persists_across_instances(self):
        pair = (sha256(SEED), sha256(glyph_of(SEED)))
        Register(self.path)["X"] = pair
        self.assertEqual(dict(Register(self.path)), {"X": pair})
        self.assertEqual(json.loads(self.path.read_text()), {"X": list(pair)})

    def test_refuses_a_malformed_file(self):
        self.path.parent.mkdir(parents=True)
        for raw in ("[]", '{"X": ["short", "pair"]}', '{"X": [1, 2]}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.path.write_text(raw)
                Register(self.path)

    def test_holds_only_hashes(self):
        Register(self.path)["X"] = (sha256(SEED), sha256(glyph_of(SEED)))
        text = self.path.read_text()
        self.assertNotIn(SEED.hex()[:64], text)
        self.assertNotIn(glyph_of(SEED).hex()[:64], text)


class ProveCommandTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("cc"):
            self.skipTest("needs a C11 compiler")
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.register = self.dir / "opx.json"
        self.seed, self.other = self.dir / "seed.bit", self.dir / "other.bit"
        self.seed.write_bytes(SEED)
        self.other.write_bytes(BIG_SEED)

    def cgs(self, *argv, authorize="", register=True):
        env = {PIXI_ENV: str(ROOT), AUTHORIZE_ENV: authorize, REGISTER_ENV: str(self.register) if register else ""}
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, env), redirect_stdout(out), redirect_stderr(err):
            code = run(list(argv))
        return code, json.loads(out.getvalue()) if code == 0 else err.getvalue()

    def prove(self, layer, name, left, right, **kwargs):
        return self.cgs(layer, "prove", name, str(left), str(right), **kwargs)

    def test_birth_needs_an_authorized_opx(self):
        self.assertEqual(self.prove("OPX", "X", self.seed, self.seed)[0], 3)
        self.assertFalse(self.register.exists())
        code, answer = self.prove("OPX", "X", self.seed, self.seed, authorize="OPX")
        self.assertEqual((code, answer), (0, {"layer": "OPX", "name": "X", "poe": "0000"}))
        self.assertIn("X", Register(self.register))

    def test_every_layer_gets_0000_or_its_own_code(self):
        self.prove("OPX", "X", self.seed, self.seed, authorize="OPX")
        for layer, refused in (("DEV", "1100"), ("USR", "1110"), ("PUB", "1111")):
            with self.subTest(layer=layer):
                self.assertEqual(self.prove(layer, "X", self.seed, self.seed)[1]["poe"], "0000")
                self.assertEqual(self.prove(layer, "X", self.seed, self.other)[1]["poe"], refused)

    def test_an_unknown_name_is_refused_below_opx(self):
        self.assertEqual(self.prove("USR", "Y", self.seed, self.seed)[1]["poe"], "1110")
        self.assertFalse(self.register.exists())

    def test_answer_carries_no_seed_glyph_or_hash(self):
        code, answer = self.prove("OPX", "X", self.seed, self.seed, authorize="OPX")
        self.assertEqual(set(answer), {"layer", "name", "poe"})

    def test_refuses_without_a_register_or_with_bad_arity(self):
        code, err = self.prove("DEV", "X", self.seed, self.seed, register=False)
        self.assertEqual(code, 2)
        self.assertIn(REGISTER_ENV, err)
        for argv in (("DEV", "prove"), ("DEV", "prove", "X", "a"), ("DEV", "prove", "X", "a", "b", "c")):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                OpFrontier().accept(argv)


if __name__ == "__main__":
    unittest.main()

"""POEX and EOPX: the Python classes wrapping the C poex and eopx microcodes (offline)."""
import hashlib
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from atcgs import EOPX, POE_CODES, POEX, PRIME_CGS, build

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
        poe = self.wallet.poe("X", lambda: BIG_SEED, self.send)
        self.assertTrue(self.wallet.exists("X"))
        self.assertEqual((poe.opx, poe.usr, poe.pub),
                         (sha256(glyph_of(BIG_SEED)), sha256(b"X"), sha256(BIG_SEED)))
        self.assertEqual(len(poe.packet()), 128)
        self.assertEqual([poe.slot(layer) for layer in PRIME_CGS], [poe.opx, poe.dev, poe.usr, poe.pub])

    def test_known_name_never_asks_its_seed_again(self):
        self.wallet.poe("X", lambda: SEED, self.send)

        def refuse():
            raise AssertionError("SEED asked for a NAME that exists in PoE")

        self.assertEqual(self.wallet.poe("X", refuse, self.send).pub, sha256(SEED))

    def test_frontier_gets_hash_seed_and_a_destroyed_dev_key(self):
        poe = self.wallet.poe("X", lambda: SEED, self.send)
        private, seed_id, existed = self.sent[0]
        self.assertEqual(seed_id, sha256(SEED))
        self.assertTrue(existed)
        self.assertFalse(private.parent.exists())
        self.assertEqual(poe.dev, sha256(self.dev_public))

    def test_dev_key_destroyed_when_send_fails(self):
        seen = []

        def send(private, seed_id):
            seen.append(private)
            raise OSError("frontier unreachable")

        with self.assertRaises(OSError):
            self.wallet.poe("X", lambda: SEED, send)
        self.assertFalse(seen[0].parent.exists())

    def test_glyph_is_never_stored_nor_delivered(self):
        glyph = glyph_of(SEED)
        poe = self.wallet.poe("X", lambda: SEED, self.send)
        for held in (repr(poe), repr(self.opx), repr(self.sent), repr(self.wallet)):
            self.assertNotIn(glyph.hex(), held)
        self.assertNotIn(glyph, poe.packet())


class SessionTests(Microcodes):
    def setUp(self):
        super().setUp()
        self.eopx.birth("X", SEED)

    def test_ladder(self):
        self.assertEqual({k: format(v, "04b") for k, v in POE_CODES.items()},
                         {"POE": "0000", "OPX": "0001", "DEV": "1001", "USR": "1101", "PUB": "1111"})

    def test_left_equals_right_is_poe(self):
        with self.wallet.session() as session:
            self.assertEqual(session.prove("X", SEED, SEED), 0b0000)
            self.assertEqual(session.poe("X"), 0b0000)

    def test_unknown_name_is_opx(self):
        with self.wallet.session() as session:
            self.assertEqual(session.prove("Y", SEED, SEED), 0b0001)

    def test_failed_control_is_dev(self):
        # BIG_SEED is not X's SEED: GLYPH(left) does not match OPX's hash(GLYPH).
        with self.wallet.session() as session:
            self.assertEqual(session.prove("X", BIG_SEED, BIG_SEED), 0b1001)

    def test_left_differs_from_right_is_pub(self):
        with self.wallet.session() as session:
            self.assertEqual(session.prove("X", SEED, BIG_SEED), 0b1111)

    def test_poe_holds_only_for_the_session(self):
        session = self.wallet.session()
        session.prove("X", SEED, SEED)
        glyph = session._glyphs["X"]
        session.close()
        self.assertEqual(bytes(glyph), bytes(8192))
        with self.assertRaises(ValueError):
            session.poe("X")
        with self.assertRaises(ValueError):
            session.prove("X", SEED, SEED)
        with self.wallet.session() as fresh, self.assertRaises(ValueError):
            fresh.poe("X")

    def test_only_a_proven_glyph_is_decorated_and_never_shown(self):
        with self.wallet.session() as session:
            session.prove("X", SEED, BIG_SEED)
            self.assertEqual(session._glyphs, {})
            session.prove("X", SEED, SEED)
            self.assertEqual(bytes(session._glyphs["X"]), glyph_of(SEED))
            self.assertNotIn(glyph_of(SEED).hex(), repr(session))


if __name__ == "__main__":
    unittest.main()

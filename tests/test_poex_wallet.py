"""POEX wallet: the Python class wrapping the C poex microcode (offline)."""
import hashlib
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from atcgs import POEX, PRIME_CGS, compress, seed_side

SEED = (Path(__file__).resolve().parents[1] / "fixtures/demo_256x256.bit").read_bytes()
BIG_SEED = bytes(range(256)) * 128  # 32768 bytes = 512x512 bits


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class SeedTests(unittest.TestCase):
    def test_seed_must_be_square_and_at_least_256(self):
        self.assertEqual(seed_side(SEED), 256)
        self.assertEqual(seed_side(BIG_SEED), 512)
        for bad in (SEED[:-1], bytes(4096), bytes(8192 + 1)):
            with self.assertRaises(ValueError):
                seed_side(bad)

    def test_compress_is_deterministic_and_256x256(self):
        glyph = compress(BIG_SEED)
        self.assertEqual(len(glyph), 8192)
        self.assertEqual(glyph, compress(BIG_SEED))
        self.assertNotEqual(glyph, compress(SEED))

    def test_minimal_seed_is_still_compressed(self):
        self.assertNotEqual(sha256(compress(SEED)), sha256(SEED))


class POEXWalletTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("cc") or not shutil.which("ssh-keygen"):
            self.skipTest("needs a C11 compiler and ssh-keygen")
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.opx = {}
        self.wallet = POEX(POEX.build(Path(self._tmp.name)), self.opx)
        self.sent = []

    def send(self, private, seed_id):
        self.sent.append((private, seed_id, private.exists()))
        self.dev_public = Path(f"{private}.pub").read_bytes().strip()

    def test_new_name_integrates_its_glyph(self):
        self.assertFalse(self.wallet.exists("X"))
        poe = self.wallet.poe("X", lambda: BIG_SEED, self.send)
        self.assertTrue(self.wallet.exists("X"))
        self.assertEqual(self.opx["X"], (sha256(BIG_SEED), sha256(compress(BIG_SEED))))
        self.assertEqual((poe.opx, poe.usr, poe.pub),
                         (sha256(compress(BIG_SEED)), sha256(b"X"), sha256(BIG_SEED)))
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
        glyph = compress(SEED)
        poe = self.wallet.poe("X", lambda: SEED, self.send)
        for held in (repr(poe), repr(self.opx), repr(self.sent)):
            self.assertNotIn(glyph.hex(), held)
        self.assertNotIn(glyph, poe.packet())

    def test_hash_seed_is_a_unique_id(self):
        self.wallet.poe("X", lambda: SEED, self.send)
        with self.assertRaises(ValueError):
            self.wallet.poe("Y", lambda: SEED, self.send)
        self.assertFalse(self.wallet.exists("Y"))

    def test_bad_seed_registers_nothing(self):
        with self.assertRaises(ValueError):
            self.wallet.poe("X", lambda: SEED[:-1], self.send)
        self.assertEqual((self.opx, self.sent), ({}, []))


if __name__ == "__main__":
    unittest.main()

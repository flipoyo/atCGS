"""Offline tests for atCGS EOPX C microcode: the birth compression (no network)."""
import hashlib
import math
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def reference(seed):
    return hashlib.shake_256(hashlib.sha256(seed).digest() + seed).digest(8192)


class EopxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.bin = pathlib.Path(cls._tmp.name) / "eopx"
        compiler = shutil.which("cc")
        if not compiler:
            raise unittest.SkipTest("no C11 compiler found")
        subprocess.run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra",
                        "-Werror", "-pedantic", "-o", str(cls.bin), str(HERE / "eopx.c")],
                       check=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def run_c(self, seed):
        return subprocess.run([str(self.bin)], input=seed, capture_output=True)

    def test_matches_the_reference_on_every_padding_case(self):
        # A square SEED is 2k^2 bytes: one side per reachable SHA-256 tail length.
        by_tail = {}
        for side in range(256, 1025, 4):
            by_tail.setdefault(side * side // 8 % 64, side)
        self.assertEqual(sorted(by_tail), [0, 2, 8, 18, 32, 34, 50])
        for side in sorted(by_tail.values()) + [1024]:
            seed = bytes((i * 31 + side) % 256 for i in range(side * side // 8))
            with self.subTest(side=side):
                result = self.run_c(seed)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, reference(seed))

    def test_refuses_non_square_or_small_seeds(self):
        for size in (0, 4096, 8191, 8193, 32767):
            with self.subTest(size=size):
                self.assertFalse(math.isqrt(size * 8) ** 2 == size * 8 and size >= 8192)
                result = self.run_c(bytes(size))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"square", result.stderr)

    def test_rejects_arguments(self):
        self.assertEqual(subprocess.run([str(self.bin), "--trace"], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

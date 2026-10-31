"""Offline tests for atCGS Layer-0 POEX C microcode (no network)."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class MicrocodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.bin = pathlib.Path(cls._tmp.name) / "poex"
        compiler = shutil.which("cc")
        if not compiler:
            raise unittest.SkipTest("no C11 compiler found")
        subprocess.run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra",
                        "-Werror", "-pedantic", "-o", str(cls.bin), str(HERE / "poex.c")],
                       check=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def run_c(self, data, mode="--packet"):
        return subprocess.run([str(self.bin), mode], input=data, capture_output=True)

    def test_declared_opx_frontier(self):
        result = subprocess.run([str(self.bin), "--contract"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().splitlines(), [
            "poex is cgitsync M.m.p opx",
            "OpFrontier serves POEX NODE DELTA OPX",
        ])

    def test_full_zero_matrix(self):
        result = self.run_c(bytes(8192))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.decode().splitlines()
        self.assertEqual(len(lines), 65)
        self.assertIn("quartet=16384", lines[63])
        self.assertIn("zeros=65536", lines[-1])
        self.assertIn("∆=0000", lines[0])
        self.assertIn("evidence=UNVERIFIED", lines[-1])

    def test_full_ones_matrix(self):
        result = self.run_c(bytes([255]) * 8192)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"zeros=0", result.stdout)

    def test_xor_delta_on_first_two_nibbles(self):
        result = self.run_c(bytes([0xA5]) + bytes(8191), "--trace")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.decode().splitlines()
        self.assertEqual(len(lines), 16385)
        self.assertIn(".poe=1010 ∆=1010 zeros=2", lines[0])
        self.assertIn(".poe=0101 ∆=1111 zeros=4", lines[1])
        self.assertIn(".poe=0000 ∆=0101 zeros=8", lines[2])

    def test_reject_short_matrix(self):
        result = self.run_c(bytes(8191))
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"expected 8192", result.stderr)

    def test_reject_long_matrix(self):
        result = self.run_c(bytes(8193))
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"exceeds 8192", result.stderr)

    def test_packet_count_and_boundary(self):
        result = self.run_c(bytes([0xF0]) * 8192)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.decode().splitlines()
        self.assertEqual(sum(line.startswith("∆ELTA packet=") for line in lines), 64)
        self.assertIn("packet=00 quartet=00256", lines[0])
        self.assertIn("packet=63 quartet=16384", lines[-2])
        self.assertIn("zeros=32768", lines[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)

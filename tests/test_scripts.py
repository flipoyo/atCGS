"""IdentityJournals M0 and M5 run end to end (test KDF profile)."""

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "ATCGS_KDF_PROFILE": "test"}


def script(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, env=ENV,
                          capture_output=True, text=True, timeout=120)


@unittest.skipUnless(shutil.which("ssh-agent"), "ssh-agent is needed")
class ScriptTests(unittest.TestCase):
    def test_identity_demo(self):
        result = script("identity_demo.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("REFUSED "), 4)
        self.assertNotIn("ACCEPTED", result.stdout)
        for line in ("agent key == granted key: True", "none found", "temporary directory removed: True"):
            self.assertIn(line, result.stdout)

    @unittest.skipUnless(all(shutil.which(t) for t in ("sshd", "git", "git-shell")), "sshd and git-shell needed")
    def test_local_remote(self):
        result = script("local_remote.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("this key is read-only (USR)", result.stdout)
        self.assertIn("Permission denied (publickey)", result.stdout)
        self.assertIn("all checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

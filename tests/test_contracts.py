import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contract_check import FIXTURES, inspect  # noqa: E402

SPEC = Path(__file__).resolve().parents[1] / "spec/contracts.toml"


def refused(test: unittest.TestCase, old: str, new: str) -> None:
    text = SPEC.read_text(encoding="utf-8")
    test.assertIn(old, text)
    with TemporaryDirectory() as d:
        f = Path(d) / "contracts.toml"
        f.write_text(text.replace(old, new, 1), encoding="utf-8")
        with test.assertRaises(ValueError):
            inspect(f)


class TestContracts(unittest.TestCase):
    def test_canonical(self):
        report = inspect()
        self.assertEqual(report["public_rows"], 4)
        self.assertEqual(report["opfrontier_rows"], 3)
        self.assertEqual((report["key_rows"], report["glyph_rows"]), (2, 2))
        self.assertFalse(report["published"])

    def test_public_tuples(self):
        self.assertEqual(
            FIXTURES["public_boundary"]["sequence"][1], ("DELTA", "POEX", "OPX", "HASH")
        )
        self.assertEqual(
            FIXTURES["public_boundary"]["sequence"][2], ("HASH", "DELTA", "CGS", "OPX")
        )
        self.assertNotIn("GLYPH", {f for row in FIXTURES["public_boundary"]["sequence"] for f in row})

    def test_key_prototype_no_longer_hashes_a_glyph(self):
        self.assertEqual(FIXTURES["key"]["prototype"][0], ("PUB", "DELTA", "POEX", "KEY"))
        refused(self, "[key]", '[key]\ndefinition = "sha256(GLYPH)"')

    def test_glyph_envelope_matches_the_code(self):
        refused(self, "bytes = 8192", "bytes = 8191")
        refused(self, "sizes = [4, 1, 12, 8159, 16]", "sizes = [4, 1, 12, 8160, 16]")
        refused(self, 'aead = "ChaCha20-Poly1305"', 'aead = "AES-GCM"')
        refused(self, "published = false  # a GLYPH", "published = true  # a GLYPH")

    def test_identity_matches_the_code(self):
        refused(self, "memory_kib = 262144", "memory_kib = 1024")
        refused(self, 'uid = "sha256(IDPUB)"', 'uid = "sha256(NAME)"')
        refused(self, 'DEV = "1000"', 'DEV = "1111"')
        refused(self, 'kdf = "Argon2id"', 'opx_pub = "qL1FhYN4yQrRd6/cOa92zPG6rsu2t8JXirlntzsYDMo="\nkdf = "Argon2id"')

    def spec_with_pin(self, directory, pin_text):
        spec = Path(directory) / "spec"
        spec.mkdir()
        (spec / "contracts.toml").write_text(SPEC.read_text(encoding="utf-8"), encoding="utf-8")
        if pin_text is not None:
            (spec / "opx.toml").write_text(pin_text, encoding="utf-8")
        return spec / "contracts.toml"

    def test_the_opx_key_is_pinned_in_spec_opx_toml_not_in_contracts(self):
        self.assertTrue(inspect()["opx_pinned"])
        self.assertNotIn("opx_pub", SPEC.read_text(encoding="utf-8").replace("opx_pub, the root", ""))
        with TemporaryDirectory() as d:
            self.assertFalse(inspect(self.spec_with_pin(d, None))["opx_pinned"])
        with TemporaryDirectory() as d:
            self.assertTrue(inspect(self.spec_with_pin(d, f'[[pin]]\nopx_pub = "{"A" * 43}="\n'))["opx_pinned"])


if __name__ == "__main__":
    unittest.main()

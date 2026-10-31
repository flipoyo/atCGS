import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contract_check import FIXTURES, candidate, inspect
from poex_4x256_simulator import (
    leaf_digest,
    merkle_branch,
    public_candidate,
    sample_matrix,
    sequence,
    split_packets,
    verify_branch,
)


class TestContracts(unittest.TestCase):
    def test_canonical(self):
        report = inspect()
        self.assertEqual(report["public_rows"], 4)
        self.assertEqual(report["opfrontier_rows"], 3)

    def test_public_tuples(self):
        self.assertEqual(
            FIXTURES["public_boundary"]["sequence"][1], ("DELTA", "POEX", "OPX", "HASH")
        )
        self.assertEqual(
            FIXTURES["public_boundary"]["sequence"][2], ("HASH", "DELTA", "CGS", "OPX")
        )
        self.assertNotIn("GLYPH", {f for row in FIXTURES["public_boundary"]["sequence"] for f in row})

    def test_key_prototype(self):
        self.assertEqual(inspect()["key_rows"], 2)
        self.assertEqual(FIXTURES["key"]["prototype"][0], ("PUB", "DELTA", "POEX", "KEY"))

    def test_key_must_hash_the_glyph(self):
        text = Path(__file__).resolve().parents[1].joinpath("spec/contracts.toml").read_text()
        with TemporaryDirectory() as d:
            f = Path(d) / "contracts.toml"
            f.write_text(text.replace('"sha256(GLYPH)"', '"GLYPH"'), encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect(f)

    def test_packet_roundtrip(self):
        data = sample_matrix()
        packets, root = sequence(data)
        self.assertEqual(len(packets), 64)
        self.assertEqual(b"".join(p.payload for p in packets), data)
        self.assertEqual(sum(p.emitted_nibble_reports for p in packets), 16384)
        self.assertEqual(len(root), 32)

    def test_all_merkle_proofs(self):
        packets, root = sequence(sample_matrix())
        leaves = [p.leaf_hash for p in packets]
        for i, p in enumerate(packets):
            self.assertTrue(verify_branch(p.leaf_hash, i, merkle_branch(leaves, i), root))
        modified = bytearray(packets[0].payload)
        modified[0] ^= 1
        self.assertFalse(
            verify_branch(leaf_digest(0, bytes(modified)), 0, merkle_branch(leaves, 0), root)
        )
        self.assertFalse(
            verify_branch(leaf_digest(0, packets[1].payload), 0, merkle_branch(leaves, 0), root)
        )

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            split_packets(sample_matrix()[:-1])

    def test_candidate_no_fake_proof(self):
        packets, root = sequence(sample_matrix())
        doc = public_candidate(packets, root)
        with TemporaryDirectory() as d:
            f = Path(d) / "candidate.json"
            f.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(candidate(f)["status"], "NOT_PUBLISHED")
            doc["poex_verified"] = True
            f.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                candidate(f)


if __name__ == "__main__":
    unittest.main()

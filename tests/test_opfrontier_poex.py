"""Validate the typed POEX descriptor without invoking the engine."""
import unittest

from atcgs import OpFrontier


class POEXFrontierTests(unittest.TestCase):
    def test_exact_descriptor(self):
        self.assertEqual(
            OpFrontier().serve_poex(), ("POEX", "NODE", "DELTA", "OPX")
        )

    def test_is_declarative_only(self):
        self.assertEqual(len(OpFrontier().serve_poex()), 4)


if __name__ == "__main__":
    unittest.main()

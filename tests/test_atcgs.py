"""Offline ALPHA frontier regressions (no Git/network/write operations)."""

import sys
import types
import unittest
from unittest.mock import Mock, patch

from atcgs import FRONTIER, OpFrontier, cgs, main


class FrontierTests(unittest.TestCase):
    def test_exact_frontier_tuple_order_and_case(self):
        self.assertEqual(FRONTIER, (
            (".opx", ("GG4G", "DELTA", "PoE", "PRIVATE")),
            (".dev", ("GX4G", "DELTA", ".opx", ".distant")),
            (".usr", ("GX4G", "DELTA", ".opx", ".local")),
            (".gts", ("CGS", "ALPHA", ".cgs", ".cgitsync")),
        ))

    def test_pass_through_preserves_all_arguments(self):
        args = ["release", "freeze", "alpha release", "--dry-run", "--force-tag", "8.5.0"]
        captured = []

        @cgs
        def handler(argv):
            captured.append(argv)
            return 17

        self.assertEqual(handler(args), 17)
        self.assertEqual(captured, [tuple(args)])
        self.assertEqual(args[0], "release")

    def test_no_invented_operation(self):
        for args in ([], ["push"], ["release"], ["release", "publish"], ["gx4g"], [".poe"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                OpFrontier().accept(args)

    def test_supported_minimal_actions(self):
        for args in (
            ["bootstrap", "install.cgs"], ["initialise", "../install.cgs"],
            ["status"], ["view-tree"], ["release", "freeze", "msg", "--dry-run"],
            ["release", "list"], ["release", "load", "8.5.0"], ["--version"],
        ):
            with self.subTest(args=args):
                self.assertEqual(OpFrontier().accept(args), tuple(args))

    def test_reaches_existing_cli_unchanged(self):
        core = Mock(return_value=42)
        package = types.ModuleType("ComplexGitSync")
        cli = types.ModuleType("ComplexGitSync.cli")
        cli.main = core
        with patch.dict(sys.modules, {"ComplexGitSync": package, "ComplexGitSync.cli": cli}):
            self.assertEqual(main(["release", "list", "--json"]), 42)
        core.assert_called_once_with(("release", "list", "--json"))


if __name__ == "__main__":
    unittest.main()

"""Offline PRIME CGS frontier regressions (no Git/network/write operations)."""

import io
import json
import os
import sys
import tomllib
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from atcgs import (
    AUTHORIZE_ENV,
    FRONTIERS,
    MOUNTS_ENV,
    PIXI_ENV,
    PRIME_CGS,
    PRIME_G,
    TRANSITIONS,
    Authorization,
    CgsMount,
    Evidence,
    MountTable,
    OpFrontier,
    Request,
    Unauthorized,
    cgs,
    public_answer,
    require_pixi,
    run,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPO = "github:example/omniscience-public"
PRIVATE_REPO = "github:example/secret-computo-repo"
PUBLIC_COMMIT = "1" * 40
PRIVATE_COMMIT = "abcdef0123456789abcdef0123456789abcdef01"
MOUNTS = f"""
[[mount]]
name = ".omniscience"
repository = "{PUBLIC_REPO}"
ref = "main"
commit = "{PUBLIC_COMMIT}"
policy = "PUBLIC"

[[mount]]
name = ".computo"
repository = "{PRIVATE_REPO}"
ref = "private-branch"
commit = "{PRIVATE_COMMIT}"
policy = "PRIVATE"
writable = true
provenance = "/home/operator/private/ledger"
"""
PRIVATE_MARKERS = (PRIVATE_REPO, "secret-computo-repo", PRIVATE_COMMIT, "private-branch", "/home/operator", ".computo")


def public_mount(**overrides):
    fields = dict(name=".omniscience", repository=PUBLIC_REPO, ref="main", commit=PUBLIC_COMMIT, policy="PUBLIC")
    return CgsMount(**{**fields, **overrides})


def private_mount(**overrides):
    fields = dict(name=".computo", repository=PRIVATE_REPO, ref="main", commit=PRIVATE_COMMIT, policy="PRIVATE")
    return CgsMount(**{**fields, **overrides})


def fake_core(result=42):
    core = Mock(return_value=result)
    package = types.ModuleType("ComplexGitSync")
    cli = types.ModuleType("ComplexGitSync.cli")
    cli.main = core
    return core, {"ComplexGitSync": package, "ComplexGitSync.cli": cli}


class Cli:
    """Run the entry point with an explicit operator environment."""

    def __init__(self, test, authorize=None, mounts=MOUNTS):
        self.dir = TemporaryDirectory()
        test.addCleanup(self.dir.cleanup)
        self.env = {AUTHORIZE_ENV: authorize or "", PIXI_ENV: str(ROOT)}
        if mounts is not None:
            path = Path(self.dir.name) / "mounts.toml"
            path.write_text(mounts, encoding="utf-8")
            self.env[MOUNTS_ENV] = str(path)
        else:
            self.env[MOUNTS_ENV] = ""

    def __call__(self, *argv, modules=None):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env), patch.dict(sys.modules, modules or {}), \
                redirect_stdout(out), redirect_stderr(err):
            code = run(list(argv))
        return code, out.getvalue(), err.getvalue()


class ContractTests(unittest.TestCase):
    def test_prime_g_without_duplicating_engine_protocol(self):
        self.assertEqual(PRIME_G, ("NAME", "NODE", "EDGE", "OP*"))

    def test_constants_match_frozen_spec(self):
        with (ROOT / "spec/contracts.toml").open("rb") as handle:
            spec = tomllib.load(handle)
        self.assertEqual(list(PRIME_CGS), spec["contract"]["prime_cgs"])
        self.assertEqual([list(edge) for edge in TRANSITIONS], spec["opfrontier"]["sequence"])
        self.assertEqual({k: list(v) for k, v in FRONTIERS}, spec["frontiers"])

    def test_exact_frontier_tuples(self):
        self.assertEqual(FRONTIERS, (
            (".poe", (".omniscience", ".cgs", "*G")),
            (".opx", (".computo", ".omniscience", ".gts")),
        ))


class TransitionTests(unittest.TestCase):
    def test_emits_exactly_three_edges(self):
        frontier = OpFrontier()
        self.assertEqual(frontier.emit("OPX", "DEV").as_tuple(), (".gts", "OPX", "DEV", ".cgs"))
        self.assertEqual(frontier.emit("DEV", "USR").as_tuple(), (".cgs", "DEV", "USR", ".toml"))
        self.assertEqual(frontier.emit("USR", "PUB").as_tuple(), (".toml", "USR", "PUB", ".omniscience"))
        self.assertEqual(len(TRANSITIONS), 3)

    def test_emission_is_never_verified(self):
        for src, dst in (("OPX", "DEV"), ("DEV", "USR"), ("USR", "PUB")):
            with self.subTest(edge=(src, dst)):
                self.assertEqual(OpFrontier().emit(src, dst).evidence, Evidence.UNVERIFIED)

    def test_denies_skip_reverse_terminal_and_invented_edges(self):
        for src, dst in (("OPX", "USR"), ("OPX", "PUB"), ("DEV", "OPX"), ("PUB", "USR"),
                         ("PUB", "OPX"), ("OPX", "OPX"), ("opx", "DEV"), ("DEV", "usr")):
            with self.subTest(edge=(src, dst)), self.assertRaises(ValueError):
                OpFrontier().emit(src, dst)

    def test_pub_is_terminal(self):
        self.assertIsNone(OpFrontier().outgoing("PUB"))
        self.assertEqual(OpFrontier().outgoing("USR").as_tuple(), TRANSITIONS[2])


class SelectorTests(unittest.TestCase):
    def test_exactly_four_case_sensitive_selectors(self):
        for layer in PRIME_CGS:
            with self.subTest(layer=layer):
                self.assertEqual(OpFrontier().accept([layer]), Request(layer))
        for layer in ("opx", "Dev", "usr", "pub", "OPX ", "CGS", "*G", ".poe"):
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                OpFrontier().accept([layer])

    def test_raw_cgitsync_commands_rejected_at_top_level(self):
        for args in ([], ["bootstrap", "x.cgs"], ["status"], ["view-tree"], ["release", "list"],
                     ["release", "freeze", "msg"], ["--version"], ["push"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                OpFrontier().accept(args)

    def test_core_operations_only_behind_opx_dev(self):
        for layer in ("OPX", "DEV"):
            for args in (["bootstrap", "install.cgs"], ["initialise", "../install.cgs"], ["status"],
                         ["view-tree"], ["release", "freeze", "msg", "--dry-run"], ["release", "list"],
                         ["release", "load", "8.5.0"], ["--version"], ["env", "show"],
                         ["env", "check", "--cgs", "examples/cgs_dev.cgs"]):
                with self.subTest(layer=layer, args=args):
                    self.assertEqual(OpFrontier().accept([layer, *args]), Request(layer, tuple(args)))
        for layer in ("USR", "PUB"):
            for args in (["status"], ["release", "list"], ["bootstrap", "x.cgs"], ["env", "show"]):
                with self.subTest(layer=layer, args=args), self.assertRaises(ValueError):
                    OpFrontier().accept([layer, *args])

    def test_no_invented_operation(self):
        for args in (["DEV", "push"], ["OPX", "release"], ["OPX", "release", "publish"],
                     ["DEV", "gx4g"], ["OPX", ".poe"], ["USR", "*G"], ["OPX", ".computo", "status"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                OpFrontier().accept(args)

    def test_level_public_override_rejected(self):
        for layer in PRIME_CGS:
            for args in (["level=PUBLIC"], ["--level", "PUBLIC"], [".computo", "level=PUBLIC"],
                         ["level=PUBLIC", ".computo"]):
                with self.subTest(layer=layer, args=args), self.assertRaises(ValueError):
                    OpFrontier().accept([layer, *args])

    def test_decorator_passes_request_unchanged(self):
        args = ["OPX", "release", "freeze", "alpha release", "--dry-run", "--force-tag", "8.5.0"]
        captured = []

        @cgs
        def handler(request):
            captured.append(request)
            return 17

        self.assertEqual(handler(args), 17)
        self.assertEqual(captured, [Request("OPX", tuple(args[1:]))])


class AuthorizationTests(unittest.TestCase):
    def test_only_private_layers_can_be_granted(self):
        self.assertEqual(Authorization.from_env({AUTHORIZE_ENV: "OPX, DEV"}).layers, {"OPX", "DEV"})
        for raw in ("USR", "PUB", "OPX,PUB", "opx", "*"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                Authorization.from_env({AUTHORIZE_ENV: raw})

    def test_require(self):
        Authorization(frozenset({"DEV"})).require("DEV")
        for layer in ("OPX", "USR", "PUB"):
            with self.subTest(layer=layer), self.assertRaises(Unauthorized):
                Authorization(frozenset({"DEV"})).require(layer)


class MountTests(unittest.TestCase):
    def test_frozen_policy_binding(self):
        for kwargs in (dict(policy="PRIVATE"), dict(name=".computo"), dict(name=".cgitsync"),
                       dict(name=".gts"), dict(writable=True), dict(writable="false")):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                public_mount(**kwargs)
        self.assertTrue(private_mount(writable=True).writable)

    def test_rejects_mutable_or_unpinned_pointers(self):
        for commit in ("", "main", "HEAD", "1" * 39, "1" * 41, "A" * 40):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                public_mount(commit=commit)
        for ref in ("", "../main", "-delete", "/etc"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                public_mount(ref=ref)
        self.assertEqual(public_mount(commit="f" * 64).commit, "f" * 64)

    def test_rejects_local_paths_and_traversal(self):
        for repository in ("github:a/..", "github:../b", "github:a/b/c", "/srv/repo", "../repo",
                           "file:///srv/repo", "ssh://git@github.com/a/b", "https://github.com/a/../b",
                           "https://../a/b", "github:a", "github:a/ b"):
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                public_mount(repository=repository)

    def test_errors_never_echo_private_repository(self):
        for kwargs in (dict(commit="main"), dict(policy="PUBLIC"), dict(ref="../x")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError) as caught:
                    private_mount(**kwargs)
                self.assertNotIn("secret-computo-repo", str(caught.exception))

    def test_duplicate_and_conflicting_identities(self):
        with self.assertRaises(ValueError):
            MountTable((public_mount(), public_mount(commit="2" * 40)))
        for repository in (PUBLIC_REPO, "https://github.com/Example/omniscience-public.git"):
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                MountTable((public_mount(), private_mount(repository=repository)))

    def test_load_rejects_unknown_or_incomplete_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mounts.toml"
            for body in ('[[mount]]\nname=".omniscience"\n',
                         MOUNTS + 'level = "PUBLIC"\n',
                         MOUNTS.replace('policy = "PRIVATE"', 'policy = "PRIVATE"\ncredentials = "x"')):
                with self.subTest(body=body[-30:]):
                    path.write_text(body, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        MountTable.load(path)

    def test_private_resolution_requires_authorized_opx_or_dev(self):
        table = MountTable((public_mount(), private_mount()))
        granted = Authorization(frozenset({"OPX", "DEV"}))
        self.assertEqual(table.resolve(".computo", "OPX", granted), private_mount())
        with self.assertRaises(Unauthorized):
            table.resolve(".computo", "DEV", Authorization())
        for layer in ("USR", "PUB"):
            with self.subTest(layer=layer), self.assertRaises(Unauthorized):
                table.resolve(".computo", layer, granted)

    def test_public_resolution_never_falls_back_to_private(self):
        table = MountTable((private_mount(),))
        for layer in PRIME_CGS:
            with self.subTest(layer=layer):
                self.assertIsNone(table.resolve(".omniscience", layer, Authorization()))
        self.assertEqual(public_answer(table)[".omniscience"], {"evidence": "unavailable"})


class EntryPointTests(unittest.TestCase):
    def test_help_is_local(self):
        code, out, _ = Cli(self)("--help")
        self.assertEqual(code, 0)
        self.assertIn("OPX,DEV,USR,PUB", out)

    def test_selector_without_argument_emits_transition(self):
        cli = Cli(self)
        for layer, edge in zip(("OPX", "DEV", "USR"), TRANSITIONS):
            with self.subTest(layer=layer):
                code, out, _ = cli(layer)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(out), {"layer": layer, "transition": list(edge), "evidence": "unverified"})

    def test_pub_serves_public_answer_without_core(self):
        code, out, _ = Cli(self)("PUB", modules={"ComplexGitSync": None, "ComplexGitSync.cli": None})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {
            "layer": "PUB",
            "frontier": {".poe": [".omniscience", ".cgs", "*G"]},
            "requestable": "*G",
            ".omniscience": {"repository": PUBLIC_REPO, "commit": PUBLIC_COMMIT, "evidence": "unverified"},
        })

    def test_pub_without_public_mount_is_unavailable(self):
        code, out, _ = Cli(self, mounts=None)("PUB")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[".omniscience"], {"evidence": "unavailable"})

    def test_no_public_output_leaks_private_material(self):
        cli = Cli(self, authorize="OPX,DEV")
        for argv in (["PUB"], ["USR"], ["PUB", ".omniscience"], ["USR", ".omniscience"],
                     ["PUB", ".computo"], ["USR", ".computo"], ["PUB", "level=PUBLIC"]):
            with self.subTest(argv=argv):
                _, out, err = cli(*argv)
                for marker in PRIVATE_MARKERS:
                    self.assertNotIn(marker, out)
                    self.assertNotIn(PRIVATE_REPO, err)
                self.assertNotIn('"verified"', out)

    def test_usr_and_pub_denied_private_even_when_owner_authorized(self):
        cli = Cli(self, authorize="OPX,DEV")
        for layer in ("USR", "PUB"):
            with self.subTest(layer=layer):
                code, out, _ = cli(layer, ".computo")
                self.assertEqual((code, out), (3, ""))

    def test_private_mount_for_authorized_operator(self):
        code, out, _ = Cli(self, authorize="DEV")("DEV", ".computo")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["repository"], PRIVATE_REPO)
        self.assertEqual(json.loads(out)["evidence"], "unverified")
        self.assertEqual(Cli(self, authorize="DEV")("OPX", ".computo")[0], 3)

    def test_core_delegation_requires_authorization(self):
        core, modules = fake_core()
        for layer in ("OPX", "DEV"):
            with self.subTest(layer=layer):
                code, _, err = Cli(self)(layer, "release", "list", modules=modules)
                self.assertEqual(code, 3)
                self.assertIn(AUTHORIZE_ENV, err)
        core.assert_not_called()

    def test_authorized_delegation_reaches_existing_cli_unchanged(self):
        core, modules = fake_core()
        code, _, _ = Cli(self, authorize="OPX")("OPX", "release", "list", "--json", modules=modules)
        self.assertEqual(code, 42)
        core.assert_called_once_with(("release", "list", "--json"))

    def test_rejections_exit_with_usage_error(self):
        core, modules = fake_core()
        cli = Cli(self, authorize="OPX,DEV")
        for argv in (["status"], ["opx"], ["USR", "status"], ["DEV", "push"], []):
            with self.subTest(argv=argv):
                self.assertEqual(cli(*argv, modules=modules)[0], 2)
        core.assert_not_called()

    def test_runs_under_pixi_only(self):
        require_pixi({PIXI_ENV: str(ROOT)})
        for env in ({}, {PIXI_ENV: ""}, {PIXI_ENV: str(ROOT.parent)}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                require_pixi(env)
        core, modules = fake_core()
        cli = Cli(self, authorize="OPX")
        cli.env[PIXI_ENV] = str(ROOT.parent)
        code, out, err = cli("OPX", "env", "show", modules=modules)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("Pixi", err)
        core.assert_not_called()

    def test_env_feature_reaches_cgitsync_unchanged(self):
        core, modules = fake_core(0)
        cli = Cli(self, authorize="DEV")
        self.assertEqual(cli("DEV", "env", "check", "--cgs", "examples/cgs_dev.cgs", modules=modules)[0], 0)
        core.assert_called_once_with(("env", "check", "--cgs", "examples/cgs_dev.cgs"))

    def test_invalid_authorization_grant_fails_closed(self):
        core, modules = fake_core()
        self.assertEqual(Cli(self, authorize="USR")("OPX", "status", modules=modules)[0], 2)
        core.assert_not_called()


if __name__ == "__main__":
    unittest.main()

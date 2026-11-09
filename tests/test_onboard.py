"""OwnerOnboarding: registration files, `OPX intake`, `OPX onboard`.

A workspace (master register, .omniscience), one project tree (register in its .memory, .omniscience), three
local bare remotes standing for GitHub, and a fake `gh`. The newcomers never type a password here: their
registration files are built from real keys and proofs.
"""

import base64
import datetime
import json
import os
import shutil
import stat
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import atcgs.commands as cmd
import atcgs.onboard as onboard
from atcgs import Authorization, OpFrontier, Unauthorized, registration
from atcgs.identity import derive
from atcgs.journal import Register
from tests.test_project_register import AUTH, OPX, enrolled, git

BOB = derive("bob", "bob passphrase", profile="test")
CHLOE = derive("chloe", "chloe passphrase", profile="test")
TODAY = datetime.date(2026, 11, 6)
URL = "https://example.test/flipoyo/{}.git"  # the git remotes, mapped to local bare repositories
REPO = "github:flipoyo/{}"  # what the registers and the .cgs name
NAMES = {"lib": "lib", "atcgs": "atCGS", "memory": ".memory", "omniscience": "omniscience"}

CGS = """project = { name = "TEST-PROJ", default_branch = "CGS-MOLO", fallback_branch = "main" }
repos = [
    { repository = "%s", relative_path = "." },
    { repository = "%s", relative_path = ".atcgs", private = true },
    { repository = "%s", relative_path = ".cgitsync/.memory", private = true, writable = true },
    { repository = "%s", relative_path = ".omniscience", private = true },
]
""" % tuple(REPO.format(n) for n in NAMES.values())

FAKE_GH = r"""#!/usr/bin/env python3
import os, pathlib, sys
state, args = pathlib.Path(os.environ["FAKE_GH"]), sys.argv[1:]
if args[:2] == ["auth", "status"]:
    if (state / "noauth").exists():
        print("You are not logged into any GitHub hosts.", file=sys.stderr); sys.exit(1)
    sys.exit(0)
if args[0] == "api":
    path = next(a for a in args if a.startswith("repos/"))
    repo = path.split("repos/")[1].split("/keys")[0]
    keys = state / (repo.replace("/", "__") + ".keys")
    lines = keys.read_text().splitlines() if keys.exists() else []
    if "-X" in args and "DELETE" in args:
        number = int(path.rsplit("/", 1)[1])
        keys.write_text("".join(line + "\n" for i, line in enumerate(lines, 1) if i != number))
        sys.exit(0)
    if path.endswith("/keys") and "-f" in args:
        if (state / "fail").exists():
            print("HTTP 422: key is already in use", file=sys.stderr); sys.exit(1)
        fields = dict(a.split("=", 1) for a in args if "=" in a and not a.startswith("repos/"))
        with keys.open("a") as handle:
            handle.write(fields["key"] + "\t" + fields["title"] + "\t" + fields["read_only"] + "\n")
        sys.exit(0)
    if path.endswith("/keys"):
        withid = any("(.id)" in a for a in args)
        for i, line in enumerate(lines, 1):
            material = " ".join(line.split("\t")[0].split()[:2])
            print(f"{i} {material}" if withid else material)
        sys.exit(0)
    if (state / ("gone-" + repo.replace("/", "__"))).exists():
        print("gh: Not Found (HTTP 404)", file=sys.stderr); sys.exit(1)
    print("false" if (state / "noadmin").exists() and ".permissions" in " ".join(args) else
          ("true" if ".permissions" in " ".join(args) else "1")); sys.exit(0)
sys.exit(2)
"""


class Setup(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cgs-onboard-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ws, self.inbox, self.intake = self.dir / "ws", self.dir / "registration", self.dir / "intake"
        self.trees = self.dir / "trees"
        self.gh_state = self.dir / "gh"
        for path in (self.ws / "examples", self.inbox, self.intake, self.trees / "TEST-PROJ-1", self.gh_state):
            path.mkdir(parents=True)
        (self.ws / "examples" / "test.cgs").write_text(CGS)
        self.remotes = {}
        for name in ("omniscience", "memory"):
            self.remotes[name] = self.bare(name)
        self.fake_gh()
        env = {"ATCGS_KDF_PROFILE": "test", "ATCGS_OPX_PUB": base64.b64encode(OPX.pub).decode(),
               "ATCGS_GLYPHS": str(self.dir / "glyphs"), "ATCGS_TREES": str(self.trees),
               "FAKE_GH": str(self.gh_state), "PATH": f"{self.dir / 'bin'}:{os.environ['PATH']}",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("ATCGS_REGISTER", "ATCGS_PROJECT", "ATCGS_IDENTITIES", "CGSHOME"):
            os.environ.pop(name, None)
        root = mock.patch.object(cmd, "ROOT", self.ws)
        root.start()
        self.addCleanup(root.stop)
        self.master_tree()
        self.project_tree()

    def bare(self, name):
        remote = self.dir / f"{name}.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(remote))
        seed = self.dir / f"seed-{name}"
        git(self.dir, "clone", "-q", str(remote), str(seed))
        (seed / "README.md").write_text(name + "\n")
        git(seed, "add", "README.md")
        git(seed, "commit", "-qm", "init")
        git(seed, "push", "-q", "origin", "HEAD:main")
        if name == "omniscience":
            git(seed, "push", "-q", "origin", "HEAD:CGS-MOLO")
        return remote

    def clone(self, name, where, branch="main"):
        git(self.dir, "clone", "-q", "-b", branch, str(self.remotes[name]), str(where))
        url = URL.format(NAMES[name])
        git(where, "config", f"url.file://{self.remotes[name]}.insteadOf", url)
        git(where, "remote", "set-url", "origin", url)

    def fake_gh(self):
        (self.dir / "bin").mkdir()
        gh = self.dir / "bin" / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    def master_tree(self):
        (self.ws / ".cgitsync" / ".memory").mkdir(parents=True)
        self.clone("omniscience", self.ws / ".omniscience")
        self.master = enrolled(self.ws / ".cgitsync" / ".memory" / ".register")
        self.keys = {
            "master-omni": cmd.SshKey.generate(REPO.format("omniscience"), "OPX"),
            "memory": cmd.SshKey.generate(REPO.format(".memory"), "OPX"),
            "project-omni": cmd.SshKey.generate(REPO.format("omniscience"), "USR"),
        }
        glyph = cmd.glyph_path(OPX.uid)
        glyph.parent.mkdir(parents=True)
        glyph.write_bytes(cmd.reseal(OPX, None, list(self.keys.values())))
        key = self.keys["master-omni"]
        self.master.grant(OPX, OPX.uid, key.repo, "OPX", key.public)

    def project_tree(self):
        tree = self.tree = self.trees / "TEST-PROJ-1"
        (tree / ".atcgs" / "spec").mkdir(parents=True)
        (tree / ".atcgs" / "spec" / "contracts.toml").write_text(
            f'[identity]\nopx_pub = "{base64.b64encode(OPX.pub).decode()}"\n')
        (tree / ".cgitsync").mkdir()
        self.clone("memory", tree / ".cgitsync" / ".memory")
        self.clone("omniscience", tree / ".omniscience", branch="CGS-MOLO")
        reg = Register(tree / ".cgitsync" / ".memory" / ".register", OPX.pub)
        shutil.copy(self.master.identity.path, reg.identity.path) if reg.identity.path.parent.exists() else None
        reg.directory.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.master.identity.path, reg.identity.path)
        for key in (self.keys["memory"], self.keys["project-omni"]):
            reg.grant(OPX, OPX.uid, key.repo, key.role, key.public)
        memory = tree / ".cgitsync" / ".memory"
        git(memory, "add", ".register")
        git(memory, "commit", "-qm", "owner grants")
        git(memory, "push", "-q", "origin", "HEAD:main")

    # a newcomer's registration file, as `request --register` writes it
    def make_registration(self, user, name, ask, keep=None, filename=None):
        pairs = registration.asked_pairs(ask, self.ws / "examples")
        keys = [{"repo": repo, "role": role, "ssh": cmd.SshKey.generate(repo, role).public} for repo, role in pairs]
        if keep is not None:
            keys = keys[:keep]
        path = self.inbox / (filename or f"{name.lower()}.toml")
        path.write_text(registration.render(name, user.uid, user.pub, user.sign(cmd.enrol_statement(user.pub)), ask, keys))
        return path

    def build_list(self, confirm=True):
        out = registration.intake(self.inbox, self.intake, self.ws / "examples", TODAY)
        path = Path(out["list"])
        if confirm:
            path.write_text(path.read_text().replace("confirmed    = false", "confirmed    = true"))
        return path


class RegistrationFileTests(Setup):
    def test_the_template_gives_the_role_to_every_repository_but_the_gate_and_the_identities(self):
        got = registration.template("TEST-PROJ", "DEV", self.ws / "examples")
        self.assertEqual({(registration.repo_path(r), ro) for r, ro in got},
                         {("flipoyo/lib", "DEV"), ("flipoyo/atcgs", "USR"), ("flipoyo/.memory", "DEV"),
                          ("flipoyo/omniscience", "USR")})

    def test_request_register_writes_a_file_the_reader_accepts(self):
        out = self.dir / "bob.toml"
        with mock.patch.object(cmd, "ask", side_effect=["bob", "bob passphrase", "bob passphrase"]):
            done = cmd.request("DEV", ("--register", "TEST-PROJ=DEV", "--name", "Bob", str(out)))
        reg = registration.read(out)
        self.assertEqual((reg.uid, reg.name, reg.ask), (BOB.uid, "Bob", {"TEST-PROJ": "DEV"}))
        self.assertEqual(len(reg.keys), 4)
        self.assertEqual(done["uid"], BOB.uid)
        registration.check_asked(reg, self.ws / "examples")
        self.assertTrue(cmd.glyph_path(BOB.uid).exists())

    def test_a_tampered_registration_is_refused(self):
        path = self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        other = base64.b64encode(derive("x", "x passphrase", profile="test").pub).decode()
        pub = base64.b64encode(BOB.pub).decode()
        path.write_text(path.read_text().replace(pub, other))
        with self.assertRaises(registration.RegistrationError):
            registration.read(path)
        path.write_text("format = 'atcgs-registration/1'\n")
        with self.assertRaises(registration.RegistrationError):
            registration.read(path)

    def test_the_example_and_the_tutorial_show_the_same_format_as_request_writes(self):
        written = tomllib.loads(registration.render(
            "Bob", BOB.uid, BOB.pub, BOB.sign(cmd.enrol_statement(BOB.pub)), {"TEST-PROJ": "DEV"},
            [{"repo": REPO.format("lib"), "role": "DEV", "ssh": cmd.SshKey.generate(REPO.format("lib"), "DEV").public}]))
        root = Path(__file__).resolve().parents[1]
        example_text = (root / "examples" / "registration.toml").read_text()
        example = tomllib.loads(example_text)

        def shape(data):
            return {k: ("any" if k == "ask" else shape(v)) if isinstance(v, dict) else type(v).__name__
                    for k, v in data.items()}

        self.assertEqual(shape(example), shape(written))
        self.assertEqual(set(example["request"]["keys"][0]), {"repo", "role", "ssh"})


class IntakeTests(Setup):
    def test_good_files_make_the_list_and_the_bad_ones_are_reported(self):
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        bad_keys = self.make_registration(CHLOE, "Short", {"TEST-PROJ": "USR"}, keep=2, filename="short.toml")
        self.assertTrue(bad_keys.exists())
        (self.inbox / "junk.toml").write_text("not = [toml")
        out = registration.intake(self.inbox, self.intake, self.ws / "examples", TODAY)
        self.assertEqual((out["persons"], out["confirmed"], len(out["problems"])), (1, 0, 2))
        listed = registration.read_list(Path(out["list"]))
        person = listed["person"][0]
        self.assertEqual((person["uid"], person["confirmed"], person["grant"]), (BOB.uid, False, {"TEST-PROJ": "DEV"}))
        self.assertEqual(listed["date"], TODAY)

    def test_intake_again_keeps_a_confirmation_only_for_an_unchanged_file(self):
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        path = self.build_list()
        again = registration.intake(self.inbox, self.intake, self.ws / "examples", TODAY)
        self.assertEqual(again["confirmed"], 1)
        self.assertEqual(Path(again["list"]), path)
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})  # a new file, new keys
        self.assertEqual(registration.intake(self.inbox, self.intake, self.ws / "examples", TODAY)["confirmed"], 0)

    def test_the_intake_verbs_are_accepted_for_opx_only(self):
        for layer, ok in (("OPX", True), ("DEV", False)):
            for args in (["intake"], ["onboard", "list.toml"], ["onboard", "list.toml", "--plan"]):
                if ok:
                    self.assertEqual(OpFrontier().accept([layer, *args]).args, tuple(args))
                else:
                    with self.assertRaises(ValueError):
                        OpFrontier().accept([layer, *args])
        for bad in (["onboard"], ["onboard", "--plan"], ["onboard", "a", "b"]):
            with self.assertRaises(ValueError):
                OpFrontier().accept(["OPX", *bad])
        OpFrontier().accept(["DEV", "request", "--register", "P=DEV", "--name", "N", "out.toml"])


class OnboardTests(Setup):
    def answers(self, count=2):
        return mock.patch.object(cmd, "ask", side_effect=["opx", "opx passphrase"][:count])

    def run_onboard(self, list_path, plan_only=False, yes=True):
        with self.answers(), mock.patch.object(onboard, "confirm", return_value="y" if yes else "n"):
            return onboard.run(AUTH, list_path, plan_only)

    def two_people(self):
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        self.make_registration(CHLOE, "Chloe", {"TEST-PROJ": "USR"})
        return self.build_list()

    def gh_keys(self):
        return sorted(line.split("\t")[1:] for f in self.gh_state.glob("*.keys") for line in f.read_text().splitlines())

    def test_plan_prints_everything_and_writes_nothing(self):
        path = self.two_people()
        before = (self.master.identity.path.read_bytes(), git(self.tree / ".cgitsync" / ".memory", "status", "--short"))
        with mock.patch.object(cmd, "ask", side_effect=AssertionError("plan asks no password")):
            plan = onboard.run(AUTH, path, plan_only=True)
        self.assertEqual({(r["person"], r["enrol"], r["grant"], r["github"]) for r in plan["plan"]},
                         {("Bob", "to do", "to do", "keys to add"), ("Chloe", "to do", "to do", "keys to add")})
        self.assertEqual(before, (self.master.identity.path.read_bytes(),
                                  git(self.tree / ".cgitsync" / ".memory", "status", "--short")))
        self.assertEqual(self.gh_keys(), [])

    def test_unconfirmed_changed_or_dirty_is_refused_and_nothing_is_done(self):
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})
        with self.assertRaisesRegex(ValueError, "no person is confirmed"):
            onboard.run(AUTH, self.build_list(confirm=False), plan_only=True)
        path = self.two_people()
        self.make_registration(BOB, "Bob", {"TEST-PROJ": "DEV"})  # replaced after intake
        with self.assertRaisesRegex(ValueError, "changed since intake"):
            onboard.run(AUTH, path, plan_only=True)
        path = self.two_people()
        (self.tree / ".cgitsync" / ".memory" / "stray.txt").write_text("mine")
        with self.assertRaisesRegex(ValueError, "outside .register"):
            onboard.run(AUTH, path, plan_only=True)

    def test_a_missing_tree_or_a_non_admin_is_refused(self):
        path = self.two_people()
        (self.gh_state / "noadmin").write_text("")
        with self.assertRaisesRegex(ValueError, "not an admin"):
            onboard.run(AUTH, path, plan_only=True)
        (self.gh_state / "noadmin").unlink()
        shutil.rmtree(self.tree)
        with self.assertRaisesRegex(ValueError, "no installed tree"):
            onboard.run(AUTH, path, plan_only=True)

    def test_one_run_does_the_whole_routine_with_one_password(self):
        path = self.two_people()
        out = self.run_onboard(path)
        self.assertEqual(out["failed"], [])
        # master: both enrolled and published
        state = Register(self.ws / ".cgitsync" / ".memory" / ".register", OPX.pub).state()
        self.assertTrue(state.is_active(BOB.uid) and state.is_active(CHLOE.uid))
        self.assertIn(BOB.uid, git(self.remotes["omniscience"], "show", "CGS-MOLO:atcgs/identity.jsonl"))
        # project: grants in its register only, with the right roles
        project = Register(self.tree / ".cgitsync" / ".memory" / ".register", OPX.pub).state()
        self.assertEqual({r.rsplit("/", 1)[-1]: g.role for r, g in project.roles(BOB.uid).items()},
                         {"lib": "DEV", "atCGS": "USR", ".memory": "DEV", "omniscience": "USR"})
        self.assertEqual({g.role for g in project.roles(CHLOE.uid).values()}, {"USR"})
        self.assertEqual(self.master.access.entries()[-1]["uid"], OPX.uid)  # the master learned no grant of theirs
        # GitHub: 8 keys, read-only exactly for USR
        keys = self.gh_keys()
        self.assertEqual(len(keys), 8)
        self.assertEqual(sorted(t for t, _ in keys if t.startswith("atCGS USR")), sorted(t for t, ro in keys if ro == "true"))
        # the register is on the memory remote, nothing else was committed
        log = git(self.remotes["memory"], "log", "--format=%s", "main").splitlines()
        self.assertEqual(log[0], "atcgs onboard 2026-11-06: 2 person(s)")
        self.assertEqual(git(self.remotes["memory"], "show", "--stat", "--format=", "main").count("stray"), 0)
        # messages, report, and the files out of the folder
        self.assertEqual(sorted(p.name for p in (self.inbox / "done" / "2026-11-06").iterdir()), ["bob.toml", "chloe.toml"])
        self.assertEqual(list(self.inbox.glob("*.toml")), [])
        text = (self.intake / "2026-11-06-Bob.txt").read_text()
        self.assertIn("pixi run cgs DEV login TEST-PROJ fetch", text)
        self.assertIn("pixi run cgitsync bootstrap examples/test.cgs TEST-PROJ", text)
        self.assertTrue((self.intake / "2026-11-06-report.json").exists())

    def test_a_second_run_changes_nothing(self):
        path = self.two_people()
        self.run_onboard(path)
        for toml in (self.inbox / "done" / "2026-11-06").iterdir():
            shutil.copy(toml, self.inbox / toml.name)
        tip = git(self.remotes["memory"], "rev-parse", "main")
        keys = self.gh_keys()
        out = self.run_onboard(path)
        self.assertEqual({s["status"] for s in out["steps"] if s["step"] in ("enrol", "deploy-key", "push")}, {"skipped"})
        self.assertEqual(git(self.remotes["memory"], "rev-parse", "main"), tip)
        self.assertEqual(self.gh_keys(), keys)

    def test_a_failure_leaves_the_file_and_a_new_run_finishes(self):
        path = self.two_people()
        (self.gh_state / "fail").write_text("")
        out = self.run_onboard(path)
        self.assertEqual(len(out["failed"]), 2)
        self.assertEqual(sorted(p.name for p in self.inbox.glob("*.toml")), ["bob.toml", "chloe.toml"])
        (self.gh_state / "fail").unlink()
        out = self.run_onboard(path)
        self.assertEqual(out["failed"], [])
        self.assertEqual(len(self.gh_keys()), 8)
        self.assertEqual(list(self.inbox.glob("*.toml")), [])

    def test_no_without_y_does_nothing(self):
        path = self.two_people()
        out = self.run_onboard(path, yes=False)
        self.assertFalse(out["applied"])
        self.assertFalse(Register(self.ws / ".cgitsync" / ".memory" / ".register", OPX.pub).state().known(BOB.uid))
        self.assertEqual(self.gh_keys(), [])

    def test_only_the_pinned_opx_runs_it(self):
        path = self.two_people()
        with mock.patch.object(cmd, "ask", side_effect=["bob", "bob passphrase"]), \
                mock.patch.object(onboard, "confirm", return_value="y"), self.assertRaises(Unauthorized):
            onboard.run(AUTH, path)
        with self.assertRaises(Unauthorized):
            onboard.run(Authorization(frozenset()), path)

    def test_the_run_leaves_the_environment_as_it_was(self):
        path = self.two_people()
        before = dict(os.environ)
        self.run_onboard(path)
        self.assertEqual(dict(os.environ), before)

    def test_the_output_never_holds_a_secret(self):
        path = self.two_people()
        out = json.dumps(self.run_onboard(path))
        report = (self.intake / "2026-11-06-report.json").read_text()
        for secret in ("opx passphrase", "bob passphrase", "PRIVATE KEY"):
            self.assertNotIn(secret, out + report)


if __name__ == "__main__":
    unittest.main()

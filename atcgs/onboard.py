"""`OPX onboard LIST [--plan]`: enrol, publish, admit, install deploy keys, push the registers.

The Owner's whole routine for newcomers, in one run, from the workspace (the master register):

    plan      read the list, verify every registration, look at every project tree and at GitHub; write nothing
    confirm   the OPX login and password, once; then one `y`
    master    enrol each new person, publish the identities
    project   per project tree: pull .omniscience, admit each person (their grants, in that register only)
    github    install each new key as a deploy key (write for OPX and DEV, read-only for USR)
    push      commit the register alone (.cgitsync/.memory/.register) and push the memory branch
    report    one line per step, and a message per newcomer

Every step is idempotent: a run that stopped halfway is run again as it is. No trust is added: every register
line is signed by the one pinned OPX key, and a project OPX cannot run this.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from atcgs import PRIVATE, Authorization, credential, pin, registration
from atcgs import commands as cmd
from atcgs.identity import Identity, uid_of
from atcgs.journal import ssh_public
from atcgs.registration import Registration, RegistrationError
from atcgs.session import AccessRefused, Session, repo_path

TREES_ENV = "ATCGS_TREES"  # where the project trees are; default ~/.cgs
confirm: Callable[[str], str] = input  # replaced in tests only


# --- GitHub, through `gh` ----------------------------------------------------------------

class GitHub:
    """The few GitHub calls onboarding needs. Reads are free; `add` is the only write."""

    def __init__(self) -> None:
        self.path = shutil.which("gh")
        self._keys: dict[str, set[str]] = {}

    def _run(self, *argv: str) -> str:
        if self.path is None:
            raise RuntimeError("gh (GitHub CLI) is not on PATH: run `pixi install` in atCGS, then `pixi run gh auth login`")
        done = subprocess.run([self.path, *argv], capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError(f"gh {' '.join(argv[:2])} failed: {(done.stderr or done.stdout).strip()}")
        return done.stdout

    def check(self) -> None:
        try:
            self._run("auth", "status")
        except RuntimeError as exc:
            if self.path is None:
                raise
            raise RuntimeError(f"{exc}\n  gh is not logged in to GitHub: run `pixi run gh auth login` once") from None

    def admin(self, repo: str) -> bool:
        return self._run("api", f"repos/{repo_path(repo)}", "--jq", ".permissions.admin").strip() == "true"

    def keys(self, repo: str) -> set[str]:
        if repo not in self._keys:
            out = self._run("api", f"repos/{repo_path(repo)}/keys", "--paginate", "--jq", ".[].key")
            self._keys[repo] = {" ".join(line.split()[:2]) for line in out.splitlines() if line.strip()}
        return self._keys[repo]

    def exists(self, repo: str) -> bool:
        """Whether the repository is still on GitHub (a 404 is False; any other failure is raised)."""
        try:
            self._run("api", f"repos/{repo_path(repo)}", "--jq", ".id")
        except RuntimeError as exc:
            if "404" in str(exc) or "Not Found" in str(exc):
                return False
            raise
        return True

    def key_ids(self, repo: str) -> dict[str, str]:
        """key material -> deploy key id, for the repositories you administer."""
        out = self._run("api", f"repos/{repo_path(repo)}/keys", "--paginate", "--jq", '.[] | "\(.id) \(.key)"')
        return {" ".join(line.split()[1:3]): line.split()[0] for line in out.splitlines() if line.strip()}

    def remove(self, repo: str, key_id: str) -> None:
        self._run("api", "-X", "DELETE", f"repos/{repo_path(repo)}/keys/{key_id}")
        self._keys.pop(repo, None)

    def add(self, repo: str, title: str, key: str, read_only: bool) -> None:
        self._run("api", f"repos/{repo_path(repo)}/keys", "-f", f"title={title}", "-f", f"key={key}",
                  "-F", f"read_only={'true' if read_only else 'false'}")
        self._keys.setdefault(repo, set()).add(" ".join(key.split()[:2]))


# --- the plan ----------------------------------------------------------------------------

@dataclass
class Entry:
    name: str
    uid: str
    reg: Registration
    grant: dict[str, str]
    pairs: dict[str, list[tuple[str, str]]]  # project -> (repository, role)


@dataclass
class Plan:
    date: datetime.date
    list_path: Path
    entries: list[Entry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    trees: dict[str, Path] = field(default_factory=dict)
    rows: list[dict[str, str]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def projects(self) -> list[str]:
        return sorted({p for e in self.entries for p in e.grant})

    def table(self) -> dict[str, object]:
        return {"date": self.date.isoformat(), "plan": self.rows, "not_confirmed": self.skipped,
                "problems": self.problems}


@contextlib.contextmanager
def in_tree(tree: Path | None) -> Iterator[None]:
    """Run as if typed in a project's gate (or, with None, in the workspace): the environment is restored."""
    saved = {name: os.environ.get(name) for name in (cmd.PROJECT_ENV, "CGSHOME")}
    try:
        if tree is None:
            os.environ.pop(cmd.PROJECT_ENV, None)
            os.environ.pop("CGSHOME", None)
        else:
            os.environ[cmd.PROJECT_ENV] = os.environ["CGSHOME"] = str(tree)
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def find_tree(project: str, given: dict[str, str]) -> Path:
    if given.get("tree"):
        tree = Path(given["tree"]).expanduser()
    else:
        base = Path(os.environ.get(TREES_ENV) or Path.home() / ".cgs")
        found = sorted(p for p in base.glob(f"{project}-*") if (p / ".atcgs").is_dir()
                       and (p / PRIVATE / ".memory").is_dir())
        if not found:
            raise RegistrationError(f"{project}: no installed tree in {base}; install it first: "
                                    f"pixi run cgitsync bootstrap examples/<file>.cgs {project}")
        tree = found[-1]
    if not ((tree / ".atcgs").is_dir() and (tree / PRIVATE / ".memory").is_dir()):
        raise RegistrationError(f"{project}: {tree} is not an installed project tree")
    return tree


def _repo_named(project: str, name: str, examples: Path) -> str:
    return next(r for r in registration.project_repos(project, examples) if repo_path(r).rsplit("/", 1)[-1] == name)


def _check_tree(project: str, tree: Path, examples: Path) -> list[str]:
    """Problems with one project tree; none means the Owner can act on it."""
    problems = []
    try:
        theirs = pin.read(tree / ".atcgs")  # spec/opx.toml, else the legacy line of contracts.toml
        if theirs != cmd.opx_pub():
            problems.append(f"{project}: its gate pins another OPX key than this workspace: update {tree}/.atcgs")
    except (OSError, ValueError):
        problems.append(f"{project}: cannot read the OPX key pinned by {tree}/.atcgs")
    with in_tree(tree):
        try:
            state = cmd.register().state()
        except (ValueError, OSError) as exc:
            return problems + [f"{project}: its register cannot be read here ({exc}); update {tree}/.atcgs"]
        owner = state.roles(uid_of(cmd.opx_pub()))
        memory, omniscience = (_repo_named(project, n, examples) for n in (".memory", "omniscience"))
        if owner.get(memory) is None or owner[memory].role != "OPX":
            problems.append(f"{project}: you hold no OPX grant on {memory} (TUTO 1, B3)")
        if owner.get(omniscience) is None:
            problems.append(f"{project}: you hold no grant on {omniscience} (TUTO 1, B3)")
    mem = tree / PRIVATE / ".memory"
    status = subprocess.run(["git", "status", "--porcelain"], cwd=mem, capture_output=True, text=True)
    if status.returncode:
        problems.append(f"{project}: {mem} is not a git repository")
    else:
        stray = [line[3:] for line in status.stdout.splitlines() if not line[3:].startswith(".register")]
        if stray:
            problems.append(f"{project}: changes in {mem} outside .register would be committed: {', '.join(stray[:5])}")
    return problems


def _entry(person: dict, examples: Path) -> Entry:
    """One confirmed person of the list, checked against their registration file."""
    name = str(person["name"])
    reg = registration.read(Path(person["registration"]))
    if reg.sha256 != person["sha256"]:
        raise RegistrationError(f"{name}: the registration file changed since intake: run OPX intake again")
    if reg.uid != person["uid"]:
        raise RegistrationError(f"{name}: the uid of the list is not the uid of the file")
    grant = {str(p): str(r) for p, r in dict(person["grant"]).items()}
    return Entry(name, reg.uid, reg, grant,
                 {project: registration.check(reg, {project: role}, examples) for project, role in grant.items()})


def _keys_of(entry: Entry, project: str) -> list[dict[str, str]]:
    return [entry.reg.key_for(repo, role) for repo, role in entry.pairs[project]]  # type: ignore[misc]


def _granted(entry: Entry, project: str, tree: Path) -> bool:
    """Whether the project's register already holds every grant of this person."""
    with in_tree(tree):
        try:
            held = cmd.register().state().roles(entry.uid)
        except (ValueError, OSError):
            return False
    return all((g := held.get(k["repo"])) is not None and (g.role, g.ssh) == (k["role"], ssh_public(k["ssh"]))
               for k in _keys_of(entry, project))


def _github_problems(plan: Plan, gh: GitHub) -> list[str]:
    """Reads only: can `gh` act, and for each key still to install, is the Owner an admin of its repository."""
    wanted: dict[str, set[str]] = {}
    for entry in plan.entries:
        for project in entry.pairs:
            for key in _keys_of(entry, project):
                if key["repo"].startswith("github:"):
                    wanted.setdefault(key["repo"], set()).add(ssh_public(key["ssh"]))
    problems = []
    try:
        gh.check()
        for repo, keys in sorted(wanted.items()):
            if keys - gh.keys(repo) and not gh.admin(repo):
                problems.append(f"{repo}: you are not an admin of it: deploy keys cannot be installed")
        for row in plan.rows:
            row["github"] = "keys to add" if any(keys - gh.keys(repo) for repo, keys in wanted.items()) else "done"
    except RuntimeError as exc:
        problems.append(f"GitHub: {exc}")
    return problems


def _rows(plan: Plan, known: object) -> None:
    for entry in plan.entries:
        for project in entry.pairs:
            if project in plan.trees:
                plan.rows.append({"person": entry.name, "project": project, "role": entry.grant[project],
                                  "enrol": "done" if known.known(entry.uid) else "to do",  # type: ignore[attr-defined]
                                  "grant": "done" if _granted(entry, project, plan.trees[project]) else "to do"})


def build_plan(list_path: Path, gh: GitHub, examples: Path) -> Plan:
    """Read everything, change nothing."""
    data = registration.read_list(list_path)
    date = data["date"] if isinstance(data["date"], datetime.date) else datetime.date.today()
    plan = Plan(date, Path(list_path).expanduser())
    if not cmd.is_master():
        plan.problems.append("onboard runs in the workspace (the master register), not in a project's gate")
        return plan
    if (branch := credential.retired_branch(cmd.project_root())) is not None:
        plan.problems.append(f"this workspace is on the retired level branch {branch}: its register lags behind the "
                             "master; install a new one with `pixi run cgs OPX init`")
        return plan
    try:
        known = cmd.register().state()
    except (ValueError, OSError) as exc:
        plan.problems.append(f"the master register cannot be read: {exc}")
        return plan
    for person in data["person"]:  # type: ignore[union-attr]
        if person.get("confirmed") is not True:
            plan.skipped.append(str(person["name"]))
            continue
        try:
            plan.entries.append(_entry(person, examples))
        except RegistrationError as exc:
            plan.problems.append(str(exc))
    if not plan.entries and not plan.problems:
        plan.problems.append("nothing to do: no person is confirmed")
    for project in plan.projects():
        try:
            plan.trees[project] = find_tree(project, data["project"].get(project, {}))  # type: ignore[union-attr]
            plan.problems += _check_tree(project, plan.trees[project], examples)
        except RegistrationError as exc:
            plan.problems.append(str(exc))
    _rows(plan, known)
    if plan.entries:
        plan.problems += _github_problems(plan, gh)
    return plan


# --- the run -----------------------------------------------------------------------------

Results = list[dict[str, str]]
_RECOVERABLE = (ValueError, OSError, RuntimeError, PermissionError)


def _step(results: Results, person: str, project: str, step: str, status: str, detail: str = "") -> None:
    results.append({"person": person, "project": project, "step": step, "status": status, "detail": detail})


def _message(entry: Entry, examples: Path) -> str:
    lines = [f"Hello {entry.name},", "", "You are registered. On your machine (the repositories are public, no key needed):", ""]
    for project, role in entry.grant.items():
        cgs = registration.project_file(project, examples).name
        lines += [f"  # {project}, as {role}",
                  "  cd ~/atCGS && git pull",
                  "  GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf \\",
                  "  GIT_CONFIG_VALUE_0=git@github.com: \\",
                  f"    pixi run cgitsync bootstrap examples/{cgs} {project}      # answer n if asked 'Run it now?'",
                  f"  cd ~/.cgs/{project}-<timestamp>/.atcgs && pixi install",
                  f"  pixi run cgs {role} login {project} fetch      # asks your login and password", ""]
    return "\n".join(lines)


def _master_phase(plan: Plan, authorization: Authorization, opx: Identity, results: Results) -> None:
    """Enrol each new person in the master register, then publish."""
    with in_tree(None):
        reg = cmd.register()
        for entry in plan.entries:
            if reg.state().known(entry.uid):
                _step(results, entry.name, "-", "enrol", "skipped", "already known")
            else:
                reg.enrol(opx, entry.reg.pub, entry.reg.proof)
                _step(results, entry.name, "-", "enrol", "done")
        out = cmd.publish(authorization, who=opx)
        _step(results, "-", "-", "publish", "done" if out["published"] else "skipped",
              str(out.get("reason", f"{out.get('lines')} line(s)")))


def _admit_phase(plan: Plan, project: str, opx: Identity, glyph: bytes, results: Results) -> None:
    """Pull the published identities into the project tree, then grant each person there."""
    with in_tree(plan.trees[project]):
        reg = cmd.register()
        with Session(opx, reg, glyph, project, "OPX") as session:
            cmd._git(session, "pull", "--ff-only", cwd=cmd.project_root() / ".omniscience")
            for entry in (e for e in plan.entries if project in e.grant):
                cmd.admit_doc(reg, opx, entry.reg.request_doc(), keys=_keys_of(entry, project))  # type: ignore[arg-type]
                _step(results, entry.name, project, "admit", "done", entry.grant[project])


def _install_key(entry: Entry, project: str, key: dict[str, str], gh: GitHub, results: Results) -> bool:
    repo, role, ssh = key["repo"], key["role"], ssh_public(key["ssh"])
    try:
        if " ".join(ssh.split()[:2]) in gh.keys(repo):
            _step(results, entry.name, project, "deploy-key", "skipped", f"{repo} {role}: already there")
        else:
            gh.add(repo, f"atCGS {role} {entry.uid[:12]}", ssh, read_only=role not in ("OPX", "DEV"))
            _step(results, entry.name, project, "deploy-key", "done", f"{repo} {role}")
    except RuntimeError as exc:
        _step(results, entry.name, project, "deploy-key", "failed", f"{repo} {role}: {exc}")
        return False
    return True


def push_register(project: str, opx: Identity, glyph: bytes, message: str) -> tuple[str, str]:
    """In the current tree: commit the register alone and push the memory branch. Never --all."""
    memory = cmd.project_root() / PRIVATE / ".memory"
    with Session(opx, cmd.register(), glyph, project, "OPX") as session:
        cmd._git(session, "add", ".register", cwd=memory)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=memory).returncode == 0:
            return "skipped", "register already pushed"
        cmd._git(session, "commit", "-m", message, cwd=memory)
        cmd._git(session, "push", "origin", "HEAD", cwd=memory)
        return "done", str(memory)


def _push_phase(plan: Plan, project: str, opx: Identity, glyph: bytes, results: Results) -> None:
    """Commit the register alone and push the memory branch. Never --all."""
    people = sum(project in e.grant for e in plan.entries)
    with in_tree(plan.trees[project]):
        status, detail = push_register(project, opx, glyph, f"atcgs onboard {plan.date.isoformat()}: {people} person(s)")
    _step(results, "-", project, "push", status, detail)


def _guarded(results: Results, who: str, project: str, step: str, call: Callable[[], object]) -> bool:
    try:
        call()
    except _RECOVERABLE as exc:
        _step(results, who, project, step, "failed", str(exc))
        return False
    return True


def _finish(plan: Plan, failed: set[str], results: Results, examples: Path) -> dict[str, object]:
    """A message each, the report, and the registration files out of the way once all went well."""
    out_dir = plan.list_path.parent
    for entry in plan.entries:
        text = re.sub(r"[^A-Za-z0-9._-]+", "_", entry.name) or entry.uid[:12]
        (out_dir / f"{plan.date.isoformat()}-{text}.txt").write_text(_message(entry, examples), encoding="utf-8")
        if entry.uid not in failed:
            done = entry.reg.path.parent / "done" / plan.date.isoformat()
            done.mkdir(parents=True, exist_ok=True)
            entry.reg.path.replace(done / entry.reg.path.name)
    report = out_dir / f"{plan.date.isoformat()}-report.json"
    report.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"applied": True, "failed": sorted(failed), "report": str(report), "steps": results}


def check_owner(plan: Plan, opx: Identity) -> bytes:
    """Before creating anyone, verify the Owner's own credentials on the trees this run uses.

    The GLYPH must exist and, for the memory and omniscience of the master and of each project tree,
    every grant must have its key in it. Returns the GLYPH bytes.
    """
    path = cmd.glyph_path(opx.uid)
    if not path.exists():
        raise AccessRefused(f"no GLYPH for this OPX login/password on this machine ({path}): "
                            "run `pixi run cgs OPX user-credential`")
    glyph = path.read_bytes()
    with in_tree(None):
        trees = [("master", cmd.project_root()), *plan.trees.items()]
    report = credential.collect(opx, glyph, trees, cmd.opx_pub())
    needed = [r for r in report["rows"] if r["granted_in"] and r["repo"].rsplit("/", 1)[-1] in (".memory", "omniscience")]  # type: ignore[attr-defined]
    bad = [f"{r['repo']} {r['role']}: {r['verdict']}" for r in needed if r["verdict"] != "ok"]
    if bad:
        raise AccessRefused("your own credentials are not in order, nothing was done: " + "; ".join(bad)
                            + " (run `pixi run cgs OPX user-credential`)")
    return glyph


def run(authorization: Authorization, list_path: Path, plan_only: bool = False,
        gh: GitHub | None = None) -> dict[str, object]:
    authorization.require("OPX")
    gh = gh or GitHub()
    examples = cmd.ROOT / "examples"
    plan = build_plan(list_path, gh, examples)
    if plan.problems or plan_only:
        if plan.problems:
            print(json.dumps(plan.table(), indent=2, ensure_ascii=False))
            raise ValueError(f"the plan has {len(plan.problems)} problem(s), nothing was done:\n- "
                             + "\n- ".join(plan.problems))
        return plan.table()
    print(json.dumps(plan.table(), indent=2, ensure_ascii=False))
    opx = cmd._opx(cmd.register(), None)
    glyph = check_owner(plan, opx)
    if confirm("Apply this plan? (y/N) ").strip().lower() not in ("y", "yes"):
        return {"applied": False, **plan.table()}
    results, failed = [], set()
    _master_phase(plan, authorization, opx, results)
    ready = [p for p in plan.projects()
             if _guarded(results, "-", p, "admit", lambda p=p: _admit_phase(plan, p, opx, glyph, results))]
    failed |= {e.uid for p in plan.projects() if p not in ready for e in plan.entries if p in e.grant}
    for entry in plan.entries:
        for project in (p for p in entry.pairs if p in ready):
            for key in _keys_of(entry, project):
                if key["repo"].startswith("github:") and not _install_key(entry, project, key, gh, results):
                    failed.add(entry.uid)
    for project in ready:
        if not _guarded(results, "-", project, "push", lambda p=project: _push_phase(plan, p, opx, glyph, results)):
            failed |= {e.uid for e in plan.entries if project in e.grant}
    return _finish(plan, failed, results, examples)

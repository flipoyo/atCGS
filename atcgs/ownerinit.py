"""`OPX init [PROJECT] [--plan] [--from PATH]`: this machine, and optionally a project, become OPX.

One command reads the state and does what is missing; a re-run changes nothing.

    no key pinned (case 1)        key, pin (spec/opx.toml, append only), enrolment, the keys of the workspace's
                                  repositories, grants, deploy keys, the pin and the register pushed, identities published
    pinned, this login (case 2)   "already OPX"; the GLYPH rebuilt if missing or incomplete (generate-glyph), else the
                                  user-credential table
    pinned, another login         refused: there is one OPX
    PROJECT (case 3)              the Owner is OPX of the project: grants on its repositories, reusing the keys the
                                  GLYPH already holds, new ones only for the rest; deploy keys; the register pushed

A workspace or a project that is not installed yet is installed first (`cgitsync bootstrap`, repositories read over
https, which are public: no key is needed to start). One login and password, one `y`.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Sequence

from atcgs import (
    PRIVATE,
    Authorization,
    Unauthorized,
    credential,
    glyphgen,
    onboard,
    pin,
    registration,
)
from atcgs import commands as cmd
from atcgs.glyph import GlyphError, SshKey, level_of, open_glyph, seal
from atcgs.identity import Identity
from atcgs.journal import Register, fingerprint, ssh_public
from atcgs.session import Session, repo_path

confirm: Callable[[str], str] = input  # replaced in tests only
WORKSPACE_FILE, WORKSPACE_NAME = "cgs-alpha.cgs", "cgs"
_HTTPS = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "url.https://github.com/.insteadOf",
          "GIT_CONFIG_VALUE_0": "git@github.com:"}  # read the public repositories without a key; remotes keep ssh


@dataclass
class Item:
    """One (repository, role) the Owner is to hold a grant for, with the key that serves it."""

    repo: str
    role: str
    key: SshKey
    new: bool  # a key made now, not one the GLYPH already had


# --- where things are ---------------------------------------------------------------------

def workspace(base: Path | None = None) -> Path | None:
    """The master tree: this atCGS when it is one, else the newest master under ~/.cgs."""
    if (cmd.ROOT / PRIVATE / ".memory").is_dir():
        if (branch := credential.retired_branch(cmd.ROOT)) is not None:
            raise ValueError(f"this workspace is on the retired level branch {branch}: its register lags behind the "
                             "master (ComplexGitSync_cgs_CGS-ALPHA). Run `pixi run cgs OPX init` from a plain atCGS "
                             "clone: it installs a new workspace from examples/cgs-alpha.cgs")
        return cmd.ROOT
    masters = [path for label, path in credential.discover(base)
               if label.startswith("master ") and credential.retired_branch(path) is None]
    return masters[-1] if masters else None


@contextlib.contextmanager
def scope(tree: Path, pub: bytes, master: bool = False) -> Iterator[None]:
    """Act in *tree*, as the master register when *master*; the OPX key is given, the environment restored."""
    names = (cmd.PROJECT_ENV, "CGSHOME", cmd.REGISTER_ENV, cmd.OPX_PUB_ENV)
    saved = {name: os.environ.get(name) for name in names}
    try:
        os.environ[cmd.PROJECT_ENV] = os.environ["CGSHOME"] = str(tree)
        os.environ[cmd.OPX_PUB_ENV] = base64.b64encode(pub).decode()
        if master:
            os.environ[cmd.REGISTER_ENV] = str(tree / PRIVATE / ".memory" / ".register")
        else:
            os.environ.pop(cmd.REGISTER_ENV, None)
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def install(cgs: Path, name: str) -> Path:
    """`cgitsync bootstrap` the tree over https, and return the new tree. The one step before the gate exists."""
    base = Path(os.environ.get(onboard.TREES_ENV) or Path.home() / ".cgs")
    before = set(base.glob(f"{name}-*"))
    tool = shutil.which("cgitsync")
    if tool is None:
        raise FileNotFoundError("cgitsync is not on PATH: run under Pixi")
    done = subprocess.run([tool, "bootstrap", str(cgs), name], env={**os.environ, **_HTTPS})
    new = sorted(set(base.glob(f"{name}-*")) - before)
    if done.returncode or not new:
        raise RuntimeError(f"cgitsync bootstrap {cgs.name} failed (exit {done.returncode})")
    return new[-1]


# --- keys, grants, the GLYPH --------------------------------------------------------------

def items_for(me: Identity, glyph_keys: Sequence[SshKey], repos: Sequence[str], role: str = "OPX") -> list[Item]:
    """For each repository, the key the GLYPH already holds for it and the role (reused), else a new one."""
    have = {(repo_path(k.repo), k.role): k for k in glyph_keys}
    return [Item(repo, role, have[(repo_path(repo), role)], False) if (repo_path(repo), role) in have
            else Item(repo, role, SshKey.generate(repo, role), True) for repo in repos]


def store_glyph(me: Identity, target: Path, old: Sequence[SshKey], items: Sequence[Item]) -> bytes:
    """Seal the old keys plus the new ones; the GLYPH grows, never shrinks; the old file is kept aside."""
    kept = [k for k in old if not any(repo_path(k.repo) == repo_path(i.repo) and k.role == i.role for i in items)]
    glyph = seal(me, [*kept, *(i.key for i in items)], min_level=level_of(target.read_bytes()) if target.exists() else 0)
    glyphgen_backup(target)
    cmd._write_private(target, glyph)
    return glyph


def glyphgen_backup(target: Path) -> None:
    if target.exists():
        import datetime
        shutil.copy2(target, target.with_name(f"{target.name}.{datetime.datetime.now():%Y%m%d%H%M%S}.bak"))


def grant_all(reg: Register, me: Identity, items: Sequence[Item]) -> int:
    """Grant each item to the Owner in *reg*; a grant that carries another key is rekeyed. Returns how many changed."""
    changed = 0
    for item in items:
        held = reg.state().roles(me.uid).get(item.repo)
        if held is None:
            reg.grant(me, me.uid, item.repo, item.role, item.key.public)
        elif held.fingerprint != fingerprint(item.key.public):
            reg.rekey(me, me.uid, item.repo, item.role, item.key.public)
        else:
            continue
        changed += 1
    return changed


def deploy_keys(gh: onboard.GitHub, me: Identity, items: Sequence[Item], steps: list[dict[str, str]]) -> None:
    """Install each key on GitHub unless it is already there (a key the GLYPH already had usually is)."""
    for item in items:
        if not item.repo.startswith("github:"):
            continue
        ssh = ssh_public(item.key.public)
        if " ".join(ssh.split()[:2]) in gh.keys(item.repo):
            continue
        gh.add(item.repo, f"atCGS {item.role} {me.uid[:12]}", ssh, read_only=item.role not in ("OPX", "DEV"))
        steps.append({"step": "deploy-key", "detail": f"{item.repo} {item.role}"})


def push_file(me: Identity, glyph: bytes, tree: Path, label: str, path: str, message: str) -> str:
    """Commit one file of the tree's root repository and push it, through the Owner's session."""
    with Session(me, cmd.register(), glyph, label, "OPX") as session:
        cmd._git(session, "add", path, cwd=tree)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=tree).returncode == 0:
            return "skipped: already committed"
        cmd._git(session, "commit", "-m", message, cwd=tree)
        cmd._git(session, "push", "origin", "HEAD", cwd=tree)
        return "done"


# --- the three cases ----------------------------------------------------------------------

def _case_new(me: Identity, ws: Path, gh: onboard.GitHub, steps: list[dict[str, str]]) -> None:
    """Case 1: no key is pinned. Everything the first OPX machine needs, in order, losing nothing."""
    target = cmd.glyph_path(me.uid)
    old = open_glyph(me, target.read_bytes()) if target.exists() else []
    repos = registration.project_repos(WORKSPACE_NAME, ws / "examples")
    items = items_for(me, old, repos)
    glyph = store_glyph(me, target, old, items)  # first: nothing below can lose the keys
    steps.append({"step": "glyph", "detail": f"{len(items)} key(s) in {target}"})
    wrote = pin.append(ws, me.pub, me.uid)
    steps.append({"step": "pin", "detail": f"{ws / pin.PIN_FILE}: {'written' if wrote else 'already pinned'}"})
    with scope(ws, me.pub, master=True):
        reg = cmd.register()
        if not reg.identity.entries():
            reg.init(me)
            steps.append({"step": "enrol", "detail": f"uid {me.uid[:12]}"})
        elif not reg.state().is_active(me.uid):
            raise Unauthorized("this master register belongs to another OPX: nothing was enrolled")
        steps.append({"step": "grant", "detail": f"{grant_all(reg, me, items)} grant(s) written"})
        deploy_keys(gh, me, items, steps)
        steps.append({"step": "push-pin", "detail": push_file(me, glyph, ws, WORKSPACE_NAME, str(pin.PIN_FILE),
                                                            "atcgs: pin the OPX key")})
        status, detail = onboard.push_register(WORKSPACE_NAME, me, glyph, f"atcgs init: {me.uid[:12]}")
        steps.append({"step": "push-register", "detail": f"{status}: {detail}"})
        out = cmd.publish(Authorization(frozenset({"OPX"})), who=me)
        steps.append({"step": "publish", "detail": "published" if out["published"] else str(out.get("reason"))})


def _public_pull(path: Path) -> None:
    """Fast-forward a public checkout (the project's .omniscience) over https: it needs no key."""
    done = subprocess.run(["git", "pull", "--ff-only"], cwd=path, env={**os.environ, **_HTTPS},
                          capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"git pull in {path} failed: {(done.stderr or done.stdout).strip()}")


def _case_project(me: Identity, tree: Path, project: str, gh: onboard.GitHub, steps: list[dict[str, str]]) -> None:
    """Case 3: the Owner is OPX of the project's tree. Keys the GLYPH already holds are reused."""
    target = cmd.glyph_path(me.uid)
    if not target.exists():
        raise ValueError("no GLYPH for this login on this machine: run `pixi run cgs OPX init` first")
    old = open_glyph(me, target.read_bytes())
    repos = registration.project_repos(project, cmd.ROOT / "examples")
    items = items_for(me, old, repos)
    glyph = store_glyph(me, target, old, items)
    steps.append({"step": "glyph", "detail": f"{sum(i.new for i in items)} new key(s), {sum(not i.new for i in items)} reused"})
    with scope(tree, me.pub):
        _public_pull(tree / ".omniscience")
        reg = cmd.register()
        cmd.sync_identities(reg)
        steps.append({"step": "grant", "detail": f"{grant_all(reg, me, items)} grant(s) written in {project}"})
        deploy_keys(gh, me, items, steps)
        status, detail = onboard.push_register(project, me, glyph, f"atcgs init {project}: {me.uid[:12]}")
        steps.append({"step": "push-register", "detail": f"{status}: {detail}"})


# --- the command --------------------------------------------------------------------------

def _parse(args: Sequence[str]) -> tuple[str | None, bool, Path | None]:
    project, plan_only, source, rest = None, False, None, list(args)
    while rest:
        word = rest.pop(0)
        if word == "--plan":
            plan_only = True
        elif word == "--from" and rest:
            source = Path(rest.pop(0)).expanduser()
        elif not word.startswith("--") and project is None:
            project = word
        else:
            raise ValueError("init [PROJECT] [--plan] [--from PATH]")
    return project, plan_only, source


def _plan(case: str, ws: Path | None, project: str | None, me: Identity) -> dict[str, object]:
    install_step = [] if ws else ["install the workspace (cgitsync bootstrap examples/cgs-alpha.cgs, over https)"]
    steps = {"new": ["make the keys of the workspace's repositories and seal them in your GLYPH", "pin your public key in "
             "spec/opx.toml (appended)", "enrol you in the master register", "grant you OPX on each repository",
             "install the deploy keys on GitHub", "commit and push the pin and the register", "publish the identities"],
             "rebuild": [*install_step, "rebuild your GLYPH for the access you already hold (generate-glyph)"],
             "project": [f"grant you OPX on every repository of {project}, reusing the keys your GLYPH has",
                         "install the deploy keys that are new", "commit and push the project's register"],
             "ok": ["nothing to do"]}[case]
    if case == "new":
        steps = [*install_step, *steps]
    return {"uid": me.uid, "case": case, "workspace": str(ws) if ws else "to install", "steps": steps}


def _decide(me: Identity, pinned: bytes | None, ws: Path | None, project: str | None) -> str:
    if project:
        return "project"
    if pinned is None:
        return "new"
    if ws is None:
        return "rebuild"
    trees = _all_trees(ws)
    glyph = cmd.glyph_path(me.uid)
    report = credential.collect(me, glyph.read_bytes() if glyph.exists() else None, trees, pinned)
    return "ok" if report["glyph"]["status"] == "ok" and report["ok"] and report["rows"] else "rebuild"  # type: ignore[index]


def behind(root: Path) -> int | None:
    """How many commits `origin/CGS-ALPHA` has that *root* lacks; None when it cannot be told (offline, no remote)."""
    env = {**os.environ, **_HTTPS}
    if subprocess.run(["git", "fetch", "--quiet", "origin", "CGS-ALPHA"], cwd=root, env=env, capture_output=True,
                      timeout=60).returncode:
        return None
    done = subprocess.run(["git", "rev-list", "--count", "HEAD..FETCH_HEAD"], cwd=root, capture_output=True, text=True)
    return int(done.stdout.strip()) if done.returncode == 0 else None


def run(authorization: Authorization, args: tuple[str, ...], gh: onboard.GitHub | None = None) -> dict[str, object]:
    authorization.require("OPX")
    project, plan_only, source = _parse(args)
    late = behind(cmd.ROOT)
    if late:
        raise ValueError(f"this atCGS is {late} commit(s) behind origin/CGS-ALPHA: run `git pull` in {cmd.ROOT} "
                         "and `pixi install`, then OPX init again")
    ws = workspace()
    pinned = (pin.read(ws) if ws else None) or _try_pin(cmd.ROOT)
    me = cmd.ask_identity("OPX", confirm=pinned is None)
    if pinned is not None and me.pub != pinned:
        raise Unauthorized("this login/password is not OPX's pinned key: there is one OPX, and it is not this login")
    if source is not None:
        return glyphgen.adopt(me, source, cmd.glyph_path(me.uid))
    case = _decide(me, pinned, ws, project)
    plan = _plan(case, ws, project, me)
    if case == "ok":
        trees = _all_trees(ws)
        glyph = cmd.glyph_path(me.uid)
        return {"__text__": credential.render(credential.collect(me, glyph.read_bytes(), trees, me.pub)), "case": case}
    if plan_only:
        return {**plan, "applied": False, "reason": "plan only"}
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    if confirm("Apply this plan? (y/N) ").strip().lower() not in ("y", "yes"):
        return {**plan, "applied": False, "reason": "declined"}
    gh = gh or onboard.GitHub()
    gh.check()
    steps: list[dict[str, str]] = []
    if ws is None:  # no valid workspace on this machine (none, or only retired ones): install one first
        ws = install(cmd.ROOT / "examples" / WORKSPACE_FILE, WORKSPACE_NAME)
        steps.append({"step": "install", "detail": str(ws)})
    if case == "rebuild":
        done = glyphgen.regenerate(me, gh=gh, trees=_all_trees(ws), assume_yes=True)
        return {**plan, **done, "steps": [*steps, *done.get("steps", [])], "case": case}  # type: ignore[misc]
    if project:
        tree = _project_tree(project, steps)
        _case_project(me, tree, project, gh, steps)
    else:
        _case_new(me, ws, gh, steps)
    return {**plan, "applied": True, "steps": steps, "case": case}


def _try_pin(root: Path) -> bytes | None:
    try:
        return pin.read(root)
    except (ValueError, OSError):
        return None


def _all_trees(ws: Path | None) -> list[tuple[str, Path]]:
    """Every tree whose register may be rewritten: the retired level trees never are."""
    trees = [(label, path) for label, path in credential.discover() if credential.retired_branch(path) is None]
    return trees or ([("master", ws)] if ws else [])


def _project_tree(project: str, steps: list[dict[str, str]]) -> Path:
    try:
        return onboard.find_tree(project, {})
    except registration.RegistrationError:
        tree = install(registration.project_file(project, cmd.ROOT / "examples"), project)
        steps.append({"step": "install", "detail": str(tree)})
        return tree


__all__ = ["run", "GlyphError"]

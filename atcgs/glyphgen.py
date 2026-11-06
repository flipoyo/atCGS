"""`generate-glyph`: get a working GLYPH back, from a copy or by regenerating the keys.

    --from PATH   take a GLYPH you still have (a file, or a folder holding it): it must open with this
                  login and password. Nothing is regenerated.
    (default)     keep the keys the GLYPH still has that match a grant, and make new keys for the others.
                  The new keys reach the registers and GitHub (the atCGS OPX), or go into a request file
                  for the Owner's `admit` (anyone else).

The private keys exist nowhere but in the GLYPH: the registers and GitHub hold public halves only. A lost
GLYPH is therefore replaced, never recovered. A repository that is no longer on GitHub gets no key.
"""

from __future__ import annotations

import datetime
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from atcgs import PRIVATE, credential, onboard
from atcgs import commands as cmd
from atcgs.glyph import GlyphError, SshKey, level_of, open_glyph, seal
from atcgs.identity import Identity
from atcgs.journal import Register, fingerprint, ssh_public
from atcgs.session import repo_path

confirm: Callable[[str], str] = input  # replaced in tests only


@dataclass
class Need:
    """One (repository, role) the identity holds a grant for."""

    repo: str
    role: str
    grants: dict[str, str] = field(default_factory=dict)  # tree label -> the ssh key granted there
    key: SshKey | None = None  # the key that will serve: one the GLYPH has, or a new one
    new: bool = False
    gone: bool = False  # the repository is no longer on GitHub


def _needs(identity: Identity, keys: Sequence[SshKey], trees: Sequence[tuple[str, Path]]) -> list[Need]:
    needs: dict[tuple[str, str], Need] = {}
    for label, path in trees:
        try:
            state = Register(path / PRIVATE / ".memory" / ".register", cmd.opx_pub()).state()
        except (ValueError, OSError):
            continue
        for repo, grant in state.roles(identity.uid).items():
            need = needs.setdefault((repo_path(repo), grant.role), Need(repo, grant.role))
            need.grants[label] = grant.ssh
    for need in needs.values():
        granted = {fingerprint(ssh) for ssh in need.grants.values()}
        need.key = next((k for k in keys if repo_path(k.repo) == repo_path(need.repo) and k.role == need.role
                         and fingerprint(k.public) in granted), None)
    return sorted(needs.values(), key=lambda n: (n.repo, n.role))


def _stale(need: Need) -> dict[str, str]:
    """The trees whose grant does not carry the key that will serve."""
    return {label: ssh for label, ssh in need.grants.items()
            if need.key is None or fingerprint(ssh) != fingerprint(need.key.public)}


def adopt(identity: Identity, source: Path, target: Path) -> dict[str, object]:
    """`--from`: take an existing GLYPH. It must open with this login and password; the old one is kept aside."""
    source = Path(source).expanduser()
    candidates = sorted(source.glob("*.glyph")) if source.is_dir() else [source]
    for candidate in candidates:
        try:
            keys = open_glyph(identity, candidate.read_bytes())
        except (GlyphError, OSError):
            continue
        if target.exists() and target.read_bytes() != candidate.read_bytes():
            target.replace(target.with_name(f"{target.name}.{datetime.datetime.now():%Y%m%d%H%M%S}.bak"))
        cmd._write_private(target, candidate.read_bytes())
        return {"adopted": str(candidate), "glyph": str(target), "keys": len(keys)}
    raise GlyphError(f"no GLYPH at {source} opens with this login and password")


def _plan(identity: Identity, keys: Sequence[SshKey], trees: Sequence[tuple[str, Path]], gh: onboard.GitHub | None,
          pinned: bool) -> list[Need]:
    needs = _needs(identity, keys, trees)
    for need in needs:
        if need.key is None:
            if gh is not None and not gh.exists(need.repo):
                need.gone = True
                continue
            need.key, need.new = SshKey.generate(need.repo, need.role), True
    return needs


def _rows(needs: Sequence[Need]) -> list[dict[str, object]]:
    return [{"repo": n.repo, "role": n.role,
             "action": "gone from GitHub: no key, its grants are revoked" if n.gone else
             ("new key" if n.new else ("re-grant the key you have" if _stale(n) else "nothing to do")),
             "trees": sorted(_stale(n)) if not n.gone else sorted(n.grants)} for n in needs]


def _apply_opx(identity: Identity, glyph: bytes, needs: Sequence[Need], trees: dict[str, Path],
               gh: onboard.GitHub, steps: list[dict[str, str]]) -> None:
    """Registers, then GitHub, then the pushes, then the old deploy keys. Repeatable."""
    todo = [n for n in needs if not n.gone and _stale(n)]
    gone = [n for n in needs if n.gone]
    for need in gone:  # 0. a repository that left GitHub keeps no grant: a session would look for its key
        for label in need.grants:
            with onboard.in_tree(trees[label]):
                cmd.register().revoke_access(identity, identity.uid, need.repo)
            steps.append({"step": "revoke", "tree": label, "detail": f"{need.repo} {need.role}: gone from GitHub"})
    for need in todo:  # 1. the registers
        for label in _stale(need):
            with onboard.in_tree(trees[label]):
                reg = cmd.register()
                reg.rekey(identity, identity.uid, need.repo, need.role, need.key.public)  # type: ignore[union-attr]
            steps.append({"step": "rekey", "tree": label, "detail": f"{need.repo} {need.role}"})
    for need in todo:  # 2. the new deploy keys
        ssh = ssh_public(need.key.public)  # type: ignore[union-attr]
        if " ".join(ssh.split()[:2]) in gh.keys(need.repo):
            steps.append({"step": "deploy-key", "tree": "-", "detail": f"{need.repo} {need.role}: already there"})
        else:
            gh.add(need.repo, f"atCGS {need.role} {identity.uid[:12]}", ssh, read_only=need.role not in ("OPX", "DEV"))
            steps.append({"step": "deploy-key", "tree": "-", "detail": f"{need.repo} {need.role}: added"})
    for label in sorted({label for n in todo for label in _stale(n)} | {label for n in gone for label in n.grants}):  # 3.
        try:
            with onboard.in_tree(trees[label]):
                status, detail = onboard.push_register(label, identity, glyph,
                                                       f"atcgs generate-glyph: {identity.uid[:12]}")
        except (PermissionError, RuntimeError, ValueError) as exc:  # e.g. no OPX grant left in that tree
            status, detail = "failed", str(exc)
        steps.append({"step": "push", "tree": label, "detail": f"{status}: {detail}"})
    for need in todo:  # 4. the old deploy keys, last: until now nothing was lost
        ids = gh.key_ids(need.repo)
        for old in {ssh_public(s) for s in _stale(need).values()}:
            key_id = ids.get(" ".join(old.split()[:2]))
            if key_id:
                gh.remove(need.repo, key_id)
                steps.append({"step": "old-deploy-key", "tree": "-", "detail": f"{need.repo}: removed {key_id}"})


def _parse(args: Sequence[str]) -> tuple[Path | None, Path | None, list[Path], bool]:
    source, out, extra, plan_only, rest = None, None, [], False, list(args)
    while rest:
        word = rest.pop(0)
        if word == "--plan":
            plan_only = True
        elif word in ("--from", "--out", "--tree") and rest:
            value = Path(rest.pop(0)).expanduser()
            source, out = (value, out) if word == "--from" else (source, value if word == "--out" else out)
            extra += [value] if word == "--tree" else []
        else:
            raise ValueError("generate-glyph [--from PATH] [--tree PATH]... [--out FILE] [--plan]")
    return source, out, extra, plan_only


def _install_glyph(me: Identity, target: Path, needs: Sequence[Need], old: Sequence[SshKey]) -> tuple[bytes, int]:
    """Seal the serving keys, plus the old keys no grant names, and write it; the old GLYPH is kept aside."""
    served = {(repo_path(n.repo), n.role): n.key for n in needs if n.key is not None}
    unique = {id(k): k for k in served.values()}.values()
    gone = {(repo_path(n.repo), n.role) for n in needs if n.gone}
    kept = [k for k in old if (repo_path(k.repo), k.role) not in served and (repo_path(k.repo), k.role) not in gone]
    previous = level_of(target.read_bytes()) if target.exists() else 0
    glyph = seal(me, [*unique, *kept], min_level=previous)  # it grows, it never shrinks
    if target.exists():
        shutil.copy2(target, target.with_name(f"{target.name}.{datetime.datetime.now():%Y%m%d%H%M%S}.bak"))
    cmd._write_private(target, glyph)
    return glyph, len(served)


def _request_file(me: Identity, work: Sequence[Need], out: Path | None) -> Path:
    """For anyone but the atCGS OPX: the new public keys, for the Owner's `admit`."""
    doc = {"uid": me.uid, "pub": cmd._b64(me.pub), "proof": cmd._b64(me.sign(cmd.enrol_statement(me.pub))),
           "keys": [{"repo": n.key.repo, "role": n.role, "ssh": n.key.public} for n in work if n.key]}  # type: ignore[union-attr]
    out = out or Path.home() / f"glyph-request-{me.uid[:8]}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def run(layer: str, args: tuple[str, ...], gh: onboard.GitHub | None = None) -> dict[str, object]:
    """`generate-glyph [--from PATH] [--tree PATH]... [--out FILE] [--plan]`."""
    source, out, extra, plan_only = _parse(args)
    return regenerate(cmd.ask_identity(layer), source, out, [(p.name, p) for p in extra] or None, plan_only, gh)


def regenerate(me: Identity, source: Path | None = None, out: Path | None = None,
               trees: Sequence[tuple[str, Path]] | None = None, plan_only: bool = False,
               gh: onboard.GitHub | None = None, assume_yes: bool = False) -> dict[str, object]:
    """Get *me* a working GLYPH: take the copy at *source*, or keep and regenerate. *me* is already derived."""
    target = cmd.glyph_path(me.uid)
    if source is not None:
        return adopt(me, source, target)
    # never overwrite a GLYPH this login cannot open: it may be someone else's (open_glyph raises)
    keys = open_glyph(me, target.read_bytes()) if target.exists() else []
    trees = list(trees or credential.discover())
    pinned = me.pub == cmd.opx_pub()
    gh = gh or (onboard.GitHub() if pinned else None)
    if gh is not None:
        gh.check()
    needs = _plan(me, keys, trees, gh, pinned)
    table: dict[str, object] = {"uid": me.uid, "glyph": str(target), "pinned": pinned, "plan": _rows(needs)}
    work = [n for n in needs if not n.gone and (n.new or _stale(n))]
    if plan_only or not (work or any(n.gone for n in needs)):
        return {**table, "applied": False, "reason": "plan only" if plan_only else "nothing to regenerate"}
    if not assume_yes:  # the caller (`OPX init`) already showed a plan and got its `y`
        print(json.dumps(table, indent=2, ensure_ascii=False))
        if confirm("Apply this plan? (y/N) ").strip().lower() not in ("y", "yes"):
            return {**table, "applied": False, "reason": "declined"}
    glyph, count = _install_glyph(me, target, needs, keys)
    steps: list[dict[str, str]] = [{"step": "glyph", "tree": "-", "detail": f"{count} key(s) in {target}"}]
    if pinned:
        _apply_opx(me, glyph, needs, dict(trees), gh, steps)  # type: ignore[arg-type]
    else:
        path = _request_file(me, work, out)
        steps.append({"step": "request", "tree": "-", "detail": f"{path}: send it to the Owner, who runs `OPX admit`"})
    return {**table, "applied": True, "steps": steps}

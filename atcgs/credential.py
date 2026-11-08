"""`user-credential`: what atCGS knows of one identity on this machine, and whether it adds up.

    GLYPH      the keys sealed in ~/.cgs/.glyph/<uid>.glyph (repository, role, fingerprint), and how full it is
    registers  the master register and each installed project tree: enrolled? revoked? which grants?
    verdict    per (repository, role): ok | no key | not admitted | revoked | refused by GitHub

It reads only. No private key, login or password is ever printed or written. With probe=True each `ok`
key is tried against its remote through the session's own ssh (never ~/.ssh).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from atcgs import PRIVATE
from atcgs.glyph import GlyphError, SshKey, open_glyph, usage
from atcgs.identity import Identity
from atcgs.journal import ROLES, JournalError, Register, fingerprint
from atcgs.session import AccessRefused, Session, repo_path

TREES_ENV = "ATCGS_TREES"  # where the trees are; default ~/.cgs (same as onboard)
VERDICTS = ("ok", "no key", "not admitted", "revoked", "refused by GitHub")


@dataclass
class TreeReport:
    label: str
    path: Path
    identity: str = "unreadable"  # enrolled | revoked | unknown | unreadable
    listed: bool = False  # is the uid in the published identities of this tree
    grants: dict[str, tuple[str, str]] = field(default_factory=dict)  # repo -> (role, fingerprint)
    error: str = ""


def discover(base: Path | None = None) -> list[tuple[str, Path]]:
    """Every tree under *base* that holds a register: the master one(s) first, then the projects."""
    base = base or Path(os.environ.get(TREES_ENV) or Path.home() / ".cgs")
    found = sorted(d for d in base.glob("*") if (d / PRIVATE / ".memory" / ".register").is_dir())
    # a project mounts atCGS read-only at .atcgs; the workspace, where atCGS is the root, does not
    master = [("master " + d.name, d) for d in found if not (d / ".atcgs").is_dir()]
    return master + [(d.name.rsplit("-", 1)[0], d) for d in found if (d / ".atcgs").is_dir()]


RETIRED_SUFFIXES = ("_opx", "_dev", "_usr")  # the level branches of the alpha series before 1.13.0


def retired_branch(tree: Path) -> str | None:
    """The memory branch of *tree* when it is a retired level branch (`ComplexGitSync_cgs_opx`), else None.

    A workspace installed on one holds a register that lags behind the master (`ComplexGitSync_cgs_CGS-ALPHA`):
    nothing must be enrolled from it. The alpha series has one branch.
    """
    done = subprocess.run(["git", "branch", "--show-current"], cwd=tree / PRIVATE / ".memory", capture_output=True, text=True)
    name = done.stdout.strip() if done.returncode == 0 else ""
    return name if name.endswith(RETIRED_SUFFIXES) else None


def _read_tree(label: str, tree: Path, identity: Identity, opx_pub: bytes) -> TreeReport:
    report = TreeReport(label, tree)
    try:
        state = Register(tree / PRIVATE / ".memory" / ".register", opx_pub).state()
    except (JournalError, ValueError, OSError) as exc:
        report.error = str(exc)
        return report
    uid = identity.uid
    report.identity = "enrolled" if state.is_active(uid) else "revoked" if state.known(uid) else "unknown"
    report.grants = {repo: (g.role, g.fingerprint) for repo, g in state.roles(uid).items()}
    published = tree / ".omniscience" / "atcgs" / "identity.jsonl"
    report.listed = published.is_file() and uid in published.read_text(encoding="utf-8")
    return report


def _glyph_keys(identity: Identity, glyph: bytes | None) -> tuple[str, list[SshKey]]:
    if glyph is None:
        return "MISSING", []
    try:
        return "ok", open_glyph(identity, glyph)
    except GlyphError as exc:
        return f"unreadable: {exc}", []


def _row(repo: str, role: str, glyph_fp: str, in_glyph: set[str], trees: Sequence[TreeReport]) -> dict[str, object]:
    held = {t.label: t.grants[r][1] for t in trees for r in t.grants
            if repo_path(r) == repo and t.grants[r][0] == role}
    known = [t for t in trees if t.identity != "unknown"]
    if held:
        verdict = "ok" if all(fp in in_glyph for fp in held.values()) else "no key"
    elif known and all(t.identity == "revoked" for t in known):
        verdict = "revoked"
    else:
        verdict = "not admitted"
    return {"repo": repo, "role": role, "fingerprint": next(iter(held.values()), glyph_fp),
            "granted_in": sorted(held), "verdict": verdict}


def collect(identity: Identity, glyph: bytes | None, trees: Sequence[tuple[str, Path]], opx_pub: bytes,
            probe: Callable[[TreeReport, Identity, bytes], set[tuple[str, str]]] | None = None) -> dict[str, object]:
    """The whole report as a dict. *probe*, if given, returns the (repo, role) pairs GitHub refused."""
    status, keys = _glyph_keys(identity, glyph)
    used, capacity = usage(keys)
    reports = [_read_tree(label, path, identity, opx_pub) for label, path in trees]
    in_glyph = {fingerprint(k.public) for k in keys}
    pairs = {(repo_path(k.repo), k.role): fingerprint(k.public) for k in keys}
    for tree in reports:
        for repo, (role, _) in tree.grants.items():
            pairs.setdefault((repo_path(repo), role), "")
    rows = [_row(repo, role, fp, in_glyph, reports) for (repo, role), fp in sorted(pairs.items())]
    refused: set[tuple[str, str]] = set()
    if probe is not None and glyph is not None:
        for tree in reports:
            refused |= probe(tree, identity, glyph)
    for row in rows:
        if row["verdict"] == "ok" and (row["repo"], row["role"]) in refused:
            row["verdict"] = "refused by GitHub"
    return {"uid": identity.uid, "pinned": identity.pub == opx_pub,
            "glyph": {"status": status, "keys": len(keys), "bytes_used": used if keys else 0, "bytes_available": capacity},
            "registers": [{"label": t.label, "path": str(t.path), "identity": t.identity, "listed": t.listed,
                           "grants": len(t.grants), "error": t.error} for t in reports],
            "rows": rows, "ok": all(r["verdict"] == "ok" for r in rows if r["granted_in"])}


def ls_remote(session: Session, repo: str) -> bool:
    """Whether the remote accepts this session's key for *repo* (one `git ls-remote`, nothing is written)."""
    done = subprocess.run(["git", "ls-remote", f"git@github.com:{repo_path(repo)}.git", "HEAD"],
                          env=session.env(), capture_output=True, text=True, timeout=60)
    return done.returncode == 0


def probe_github(tree: TreeReport, identity: Identity, glyph: bytes,
                 test: Callable[[Session, str], bool] = ls_remote) -> set[tuple[str, str]]:
    """The (repo, role) pairs of this tree whose key GitHub refuses; one session per role."""
    from atcgs.commands import opx_pub

    refused: set[tuple[str, str]] = set()
    register = Register(tree.path / PRIVATE / ".memory" / ".register", opx_pub())
    for role in sorted({role for role, _ in tree.grants.values()} & set(ROLES)):
        try:
            with Session(identity, register, glyph, "user-credential", role) as session:
                refused |= {(repo_path(repo), role) for repo, grant in session.grants.items()
                            if grant.role == role and not test(session, repo)}
        except (AccessRefused, GlyphError, OSError, subprocess.SubprocessError):
            continue
    return refused


def render(report: Mapping[str, object]) -> str:
    glyph, lines = report["glyph"], []
    lines.append(f"uid      {report['uid']}" + ("   (atCGS OPX: the pinned key)" if report["pinned"] else ""))
    if glyph["status"] == "ok":  # type: ignore[index]
        lines.append(f"glyph    {glyph['keys']} key(s), {glyph['bytes_used']} of {glyph['bytes_available']} bytes used")  # type: ignore[index]
    else:
        lines.append(f"glyph    {glyph['status']}" + ("   <- no login can work on this machine until a GLYPH holds the keys"  # type: ignore[index]
                                                     if glyph["status"] == "MISSING" else ""))  # type: ignore[index]
    lines += ["", "register".ljust(26) + "identity    grants  published"]
    for reg in report["registers"]:  # type: ignore[attr-defined]
        note = reg["error"] or ("listed" if reg["listed"] else "-")
        lines += [f"{reg['label']:<26}{reg['identity']:<12}{reg['grants']:<8}{note}", f"  {reg['path']}"]
    if not report["registers"]:
        lines.append("(none: no tree of atCGS on this machine; the Owner's `OPX init` installs the workspace, "
                     "anyone else installs a project, TUTO 1 Part D)")
    lines += ["", "repository".ljust(36) + "role  " + "fingerprint".ljust(24) + "granted in / verdict"]
    for row in report["rows"]:  # type: ignore[attr-defined]
        lines.append(f"{row['repo']:<36}{row['role']:<6}{row['fingerprint'][:22]:<24}"
                     f"{', '.join(row['granted_in']) or '-'}  {row['verdict'].upper() if row['verdict'] != 'ok' else 'ok'}")
    return "\n".join(lines)

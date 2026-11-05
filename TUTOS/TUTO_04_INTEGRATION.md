# TUTO 04 — Integration: what is checked, and what is still open

**Goal:** run every check this repository has, in one place, and see which parts of
the system are not yet built.

This tutorial replaces the earlier 24-hour roadmap. It listed windows and deliverables
that were planning, not software state. Open work is now listed in README § 8 and in
the open tickets under `local/.dev/.ticket/`.

## 1. Run every check

```bash
pixi install
pixi run lint                  # ruff, rules from ComplexGitSync
pixi run test                  # tests/: contracts, layers, identity, session, scripts
pixi run contract-inspect      # spec/contracts.toml against the code
pixi run identity-demo         # identity flow on throwaway data
pixi run local-remote          # same flow against a local sshd
pixi run cgitsync validate examples/cgs-opx.cgs
pixi run cgitsync validate examples/cgs-dev.cgs
pixi run cgitsync validate examples/cgs-usr.cgs
pixi run cgitsync validate examples/ComplexGraphSync.cgs
```

Expected results:
- `lint`: `All checks passed!`
- `test`: `passed` with no failures.
- `contract-inspect`: `"status": "VALIDATED_SYNTAX"`.
- `identity-demo`: four lines starting `REFUSED`, then `temporary directory removed: True`.
- `local-remote`: `all checks passed`.
- each `validate`: `DECLARED`.

`local-remote` needs `sshd` and `git-shell`. The test suite skips it when they are
missing, so a green `test` run does not prove it ran.

## 2. The dogfood environment

```bash
pixi run -e dogfood test
```

This runs the same suite against the `./ComplexGitSync` checkout instead of the
pinned revision. Use it when changing both repositories.

## 3. Built and checked

| Part | Where | Checked by |
|---|---|---|
| Levels and codes from ComplexGitSync | `atcgs/__init__.py`, `commands.py` | `test_layers` |
| Journals: enrol, rotate, revoke, grant | `atcgs/journal.py` | `test_identity_layer` |
| GLYPH: seal and open, one bit refused | `atcgs/glyph.py` | `test_identity_layer` |
| Session: one key per repo, agent cleaned up | `atcgs/session.py` | `test_identity_layer`, `local-remote` |
| Per-level cgitsync verbs through `login` | `LOGIN_OPS` | `test_identity_layer::SelectorTests` |
| Level trees and workspace tree validate | `examples/` | `test_layers`, `cgitsync validate` |

## 4. Not built

Each item is stated in README § 8:
- OPX key pinning is a manual step for the owner (TUTO 01 § 3); it is done for
  this workspace.
- DEV and USR login is not yet proven on their own trees (`cgs-dev.cgs`,
  `cgs-usr.cgs`).
- Deploy keys are printed, not installed: OPX runs the printed `gh api` commands.
- `@cgs … commit` keeps only one line of a commit message.
- Nothing is projected to `.omniscience`.
- No checkpoint is verified; every evidence value is `unverified`.

## 5. Definition of done for an integration change

A change to atCGS is integrated when:
- `pixi run lint` and `pixi run test` pass;
- `pixi run contract-inspect` passes after any change to `spec/contracts.toml`;
- each level tree still validates with `cgitsync validate`;
- README § 2 and § 8 match what the change did.

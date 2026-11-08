# Tuto1OpxInit — CorrPlan: TUTO 1 Part A and B fail on a fresh Owner machine

*Created: 2026-11-08*

*Branch: CGS-ALPHA*

> **Owner report — 2026-11-08:** *"I am on tuto1. I have my OPX but the first part failed. […] I don't get
> what B1 is for? Then B3 fails. […] running tuto1 section1 gives me the feeling that nothing works, as well
> as B. You must correct what is necessary."*

## What happened

On `remanence`, from a plain clone of atCGS (`CGS-ALPHA`, 1.13.0-alpha, `pixi install` done):

| Step of TUTO 1 | Command | Result |
|---|---|---|
| A | `pixi run cgs OPX init --plan` | `OPX requires explicit owner authorization (ATCGS_AUTHORIZE)`: the TUTO shows `--plan` without it |
| A | `ATCGS_AUTHORIZE=OPX pixi run cgs OPX init` | plan `rebuild` printed, `y`, then a **traceback**: `RuntimeError: gh is not on PATH` |
| A | `pixi run cgs OPX user-credential` | `glyph MISSING`, no register: correct, but says nothing of what to do |
| A | `pixi run cgs OPX generate-glyph --plan` | the same traceback |
| B3 | `ATCGS_AUTHORIZE=OPX pixi run cgs OPX init MOLO-HRDW` | plan `project` printed, `y`, the same traceback; with `gh` it would have stopped on `no GLYPH` anyway |

## Causes

1. **`gh` is required but not provided.** `OPX init`, `generate-glyph` (Owner) and `OPX onboard` call the
   GitHub CLI; `pixi.toml` does not declare it and TUTO 1 never says to install it or to log it in
   (`gh auth login`). `remanence` has no `gh`.
2. **The check comes after the `y`.** `ownerinit.run` asks `Apply this plan?` and only then runs
   `gh.check()`. `--plan` cannot show the problem.
3. **A `RuntimeError` escapes as a traceback.** `atcgs.run` turns `ValueError`, `OSError` and
   `PermissionError` into `@cgs: …`; every `RuntimeError` (gh, git, cgitsync failing) is a traceback.
4. **B3's plan ignores a missing GLYPH.** Case `project` reuses the GLYPH; without one it can only fail, but
   the plan says nothing and asks `y`.
5. **TUTO 1 is wrong in places.** `--plan` without `ATCGS_AUTHORIZE`; B1 does not say it is for a *new*
   project only (MOLO-HRDW is already declared in `examples/molo_hrdw.cgs`) and logs in as
   `ComplexGraphSync` while the workspace is `cgs`; B2 says it is "the only step that uses your personal
   GitHub access", which `gh` contradicts; nothing says A must succeed before B3.
6. **The authorization refusal does not say how to authorize.**

## Corrections

| # | Where | Change |
|---|---|---|
| K1 | `pixi.toml` | `gh` in `[dependencies]` (conda-forge, linux-64, win-64, osx-arm64); `pixi.lock` updated |
| K2 | `atcgs/onboard.py` `GitHub` | errors name the fix: `gh is not on PATH: run pixi install …`, `gh auth status failed … run pixi run gh auth login` |
| K3 | `atcgs/ownerinit.py` `run` | the plan carries `problems` (gh not ready, case `project` with no GLYPH); `--plan` shows them; an applied run with problems stops **before** `Apply this plan?` |
| K4 | `atcgs/__init__.py` `run` | `RuntimeError` → `@cgs: …`, exit `1` (the world failed: gh, git, cgitsync), no traceback; ALPHA.md exit codes |
| K5 | `atcgs/__init__.py` `Authorization.require` | the refusal shows the line to type: `ATCGS_AUTHORIZE=OPX pixi run cgs OPX …` |
| K6 | `atcgs/credential.py` `render` | no register found: one line saying how to get one |
| K7 | `TUTOS/TUTO_1_OPERATE_A_PROJECT.md` | A: `gh auth login` once, `ATCGS_AUTHORIZE=OPX` on `--plan`; B1: only for a new project, skip for MOLO-HRDW, workspace login `cgs`; B2: optional, B3 installs the tree; B3: after A; troubleshooting rows |
| K8 | `tests/test_ownerinit.py` | gh missing: `--plan` lists it, an applied run stops before the `y` and writes nothing; B3 with no GLYPH refused before the `y`; RuntimeError gives exit 1 without traceback |

Not changed: `--plan` still needs `ATCGS_AUTHORIZE=OPX` (every OPX verb does; the TUTO is corrected instead).

## Acceptance

- `pixi run test` and `pixi run lint` green.
- `pixi install` then `pixi run gh --version` works on `remanence`.
- `ATCGS_AUTHORIZE=OPX pixi run cgs OPX init --plan` without `gh auth login` prints the plan with the gh
  problem; with it, `OPX init` rebuilds the GLYPH (case `rebuild`), then `OPX init MOLO-HRDW` succeeds.
  *These last two are the Owner's run: they need the Owner's login and GitHub.*

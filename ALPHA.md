# @cgs — PRIME CGS entry point

The `@cgs` name is simultaneously a **Pixi task** and a **Python decorator**.
Its `OpFrontier` accepts exactly four case-sensitive System Layer selectors,
`PRIME CGS = {OPX, DEV, USR, PUB}`. Raw `cgitsync` verbs are **not** top-level
`@cgs` commands: they are reachable only behind an authorized `OPX`/`DEV`
selector, then passed unchanged to `ComplexGitSync.cli.main`, which routes
mutating operations via `RoutedClient -> Op`.

Inner version: `1.4.0-alpha` (SemVer 2.0.0; the ALPHA stage is the `-alpha`
prerelease). Its single source is `atcgs.__version__`; `@cgs --version` prints it.

**Build name.** The project is `CGS`; its build is the executable in the Pixi
environment, named `cgs` (`@cgs` and `cgitsync` are two names for that one
build). The name is lower-case(project), or `build-name` when set, in
`pixi.toml` `[tool.cgs]`. Commit subjects are `<build-name>-<version>`:
`atcgs.commit_subject()`.

**Pixi only.** `@cgs` and the scripts refuse to start outside this repository's
Pixi environment (`PIXI_PROJECT_ROOT`, exit `2`). `pixi.toml` keeps the pinned
ComplexGitSync's channels, platforms, Python and tools, and `ruff.toml` its lint
rules, so `@cgs` and `cgitsync` share one environment. Every command is a task:
`@cgs`, `test`, `lint`, `contract-inspect`, `contract-candidate`,
`poex-candidate`, `microcode-test`.

```bash
pixi install
pixi run '@cgs' --help
pixi run '@cgs' --version    # ComplexGraphSync 1.4.0-alpha (local, no cgitsync)
pixi run '@cgs' OPX          # emits .gts OPX DEV .cgs (evidence: unverified)
pixi run '@cgs' DEV          # emits .cgs DEV USR .toml
pixi run '@cgs' USR          # emits .toml USR PUB .omniscience
pixi run '@cgs' PUB          # read-only PUBLIC answer: .poe {.omniscience, .cgs, *G}
pixi run '@cgs' USR .omniscience   # resolve the PUBLIC mount
# Stateful operations need an explicit owner grant (OPX and/or DEV):
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX bootstrap example.cgs
ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV status
ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV release freeze "ALPHA release" --dry-run
ATCGS_AUTHORIZE=OPX,DEV pixi run '@cgs' DEV .cgitsync   # resolve the PRIVATE mount
ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV env check --cgs examples/cgs_dev.cgs
ATCGS_REGISTER=opx.json ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX prove X seed.bit seed.bit  # birth, then .poe
ATCGS_REGISTER=opx.json pixi run '@cgs' USR prove X left.bit right.bit   # {"poe": "0000"} or "1110"
pixi run test
pixi run lint
```

Exit codes: `0` success, `2` rejected request (unknown selector, raw verb,
override such as `level=PUBLIC`), `3` unauthorized (missing grant, or `USR`/`PUB`
asking for `.cgitsync`).

## Selectors

| Selector | Without argument | With argument |
| --- | --- | --- |
| `OPX` | emit `.gts OPX DEV .cgs` | authorized `cgitsync` verb, or `.cgitsync`/`.omniscience` |
| `DEV` | emit `.cgs DEV USR .toml` | authorized `cgitsync` verb, or `.cgitsync`/`.omniscience` |
| `USR` | emit `.toml USR PUB .omniscience` | `.omniscience` only |
| `PUB` | PUBLIC answer (terminal layer) | `.omniscience` only |

- Exactly three edges exist; `PUB` is terminal. Skipped, reversed or invented
  edges are refused by `OpFrontier.emit`.
- `ATCGS_AUTHORIZE` is operator configuration, never read from the request
  arguments. It may grant only `OPX` and/or `DEV`; `USR` cannot be elevated
  and is always denied `.cgitsync`.
- `PUB` never imports ComplexGitSync, needs no `cgitsync` bootstrap and never
  mutates a GitRepo.
- Emitted transitions and mount views report `evidence: unverified`, or
  `unavailable` when no PUBLIC mount is configured. No independent
  `.omniscience` verifier exists yet, so nothing is ever reported `verified`.

## The environment feature

`cgitsync env show|check` reaches cgitsync through OpFrontier like any other
verb (`OPX`/`DEV`, with `ATCGS_AUTHORIZE`). Each `cgs-*.cgs` tree declares the
same `[environment]` (Python from `pixi.toml`, Git, Pixi, manifest `pixi.toml`,
`environment_root = "root"`), so the drift `env check` reports for @cgs is the
one cgitsync reports for itself. `tests/test_layers.py` keeps them in step.

## Layer trees: cgs_opx.cgs, cgs_dev.cgs, cgs_usr.cgs

`POEX.cgs` at the root is the **PUB** install, the `install.cgs` of atCGS, and
mounts nothing private. `examples/cgs_{opx,dev,usr}.cgs` install the other
levels, mirroring ComplexGitSync's `complexgitsync-{opx,dev,usr}.cgs` and the
gate pattern of `gx4g-*.cgs`. Every level is project `cgs` on `CGS-ALPHA`, falling back to `main`. The files are named `cgs_<level>.cgs`, not `cgs-<level>.cgs`: ComplexGitSync reads the dashed shape as a contract that asks for the level as the branch.

| Mount | OPX | DEV | USR |
| --- | --- | --- | --- |
| `.omniscience`: `codeberg:GX4G/.omniscience`, the ledger, branch `cgs_CGS-ALPHA` | writable | no | never |
| `.agent/.distant`: `.ticketing`, `DevSpec`, `DocSpec` | read-only | read-only | no |
| `.agent/.local`: `.dev`, `.localSpec`, `.claude`, branch `cgs_CGS-ALPHA` | writable | writable | no |

```bash
pixi run cgitsync bootstrap examples/cgs_dev.cgs cgs
```

The Operating Space reads `.omniscience` and `.cgitsync`. `.cgitsync` is not a
mount: it is cgitsync's own directory, which no tree mounts ComplexGitSync into.
`.omniscience` holds the ledger at the tree's root, the way the gate holds the
register in a GX4G Operating Space. The mount points are separate Git
repositories, listed in `.gitignore` with `.cgitsync/`.

## @cgs mounts

`@cgs` mounts are **unrelated** to `@cgitsync` GitTree/Memory mounts. The
PRIVATE mount is `.cgitsync` (formerly `.computo`). They are declared in an operator TOML file
named by `ATCGS_MOUNTS`:

```toml
[[mount]]
name = ".omniscience"         # PUBLIC, must be read-only
repository = "github:<owner>/<public-repo>"
ref = "main"
commit = "<full 40- or 64-hex commit id>"
policy = "PUBLIC"

[[mount]]
name = ".cgitsync"             # PRIVATE, OPX/DEV with ATCGS_AUTHORIZE only
repository = "github:<owner>/<private-repo>"
ref = "main"
commit = "<full commit id>"
policy = "PRIVATE"
writable = true
```

Refused: any name other than `.omniscience`/`.cgitsync`, a policy that differs
from the frozen binding, a writable PUBLIC mount, a ref not pinned to a full
commit, local paths, `file:`/`ssh:` URLs, path traversal, unknown fields,
duplicate names and one GitRepo backing both PUBLIC and PRIVATE. Error
messages name the mount, never the repository. The PUBLIC view exposes only
`repository`, `commit` and `evidence`.

## Limits

- `@cgs` does **not** create or verify Merkle roots, `.gts` proofs or PoE, and
  does not fetch GitRepos: mount resolution is declarative.
- It does **not** implement CGS-BETA, GX4G or `*G` requestability.
- PRIME G is `{NAME, NODE, EDGE, OP*}`. Existing CGS-ALPHA `Op` remains authoritative.
- `cgitsync release freeze` tags `<project-name>-<version>`, where the version
  comes from the **target GitTree root's** `pixi.toml`, not `atCGS/pixi.toml`.
  `--force-tag` is an existing CGS-ALPHA override, never set by the adapter.
- The dependency is fixed to a reviewed CGS-ALPHA commit (ComplexGitSync 8.6.2,
  `9594d7e`); no unlocked branch update can silently replace its invariants.
- `pixi.lock` is generated by `pixi install` against that pin and committed.
- Test `release freeze` in a disposable GitTree before permitting pushes to a
  production project. Even an accepted request can still fail safely inside
  `cgitsync` because of workspace/integrity/permission guards.
- This is a **breaking `@cgs` API change** (raw verbs → selectors) for `@cgs`
  callers only; ComplexGitSync state requires no migration.

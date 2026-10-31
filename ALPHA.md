# @cgs — PRIME CGS entry point

The `@cgs` name is simultaneously a **Pixi task** and a **Python decorator**.
Its `OpFrontier` accepts exactly four case-sensitive System Layer selectors,
`PRIME CGS = {OPX, DEV, USR, PUB}`. Raw `cgitsync` verbs are **not** top-level
`@cgs` commands: they are reachable only behind an authorized `OPX`/`DEV`
selector, then passed unchanged to `ComplexGitSync.cli.main`, which routes
mutating operations via `RoutedClient -> Op`.

Inner version: `0.1.0-alpha` (SemVer 2.0.0; the ALPHA stage is the `-alpha`
prerelease). Its single source is `atcgs.__version__`; `@cgs --version` prints it.

```bash
pixi install
pixi run '@cgs' --help
pixi run '@cgs' --version    # ComplexGraphSync 0.1.0-alpha (local, no cgitsync)
pixi run '@cgs' OPX          # emits .gts OPX DEV .cgs (evidence: unverified)
pixi run '@cgs' DEV          # emits .cgs DEV USR .toml
pixi run '@cgs' USR          # emits .toml USR PUB .omniscience
pixi run '@cgs' PUB          # read-only PUBLIC answer: .poe {.omniscience, .cgs, *G}
pixi run '@cgs' USR .omniscience   # resolve the PUBLIC mount
# Stateful operations need an explicit owner grant (OPX and/or DEV):
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX bootstrap example.cgs
ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV status
ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV release freeze "ALPHA release" --dry-run
ATCGS_AUTHORIZE=OPX,DEV pixi run '@cgs' DEV .computo   # resolve the PRIVATE mount
pixi run test
```

Exit codes: `0` success, `2` rejected request (unknown selector, raw verb,
override such as `level=PUBLIC`), `3` unauthorized (missing grant, or `USR`/`PUB`
asking for `.computo`).

## Selectors

| Selector | Without argument | With argument |
| --- | --- | --- |
| `OPX` | emit `.gts OPX DEV .cgs` | authorized `cgitsync` verb, or `.computo`/`.omniscience` |
| `DEV` | emit `.cgs DEV USR .toml` | authorized `cgitsync` verb, or `.computo`/`.omniscience` |
| `USR` | emit `.toml USR PUB .omniscience` | `.omniscience` only |
| `PUB` | PUBLIC answer (terminal layer) | `.omniscience` only |

- Exactly three edges exist; `PUB` is terminal. Skipped, reversed or invented
  edges are refused by `OpFrontier.emit`.
- `ATCGS_AUTHORIZE` is operator configuration, never read from the request
  arguments. It may grant only `OPX` and/or `DEV`; `USR` cannot be elevated
  and is always denied `.computo`.
- `PUB` never imports ComplexGitSync, needs no `cgitsync` bootstrap and never
  mutates a GitRepo.
- Emitted transitions and mount views report `evidence: unverified`, or
  `unavailable` when no PUBLIC mount is configured. No independent
  `.omniscience` verifier exists yet, so nothing is ever reported `verified`.

## @cgs mounts

`@cgs` mounts are **unrelated** to `@cgitsync` GitTree/Memory mounts and to
`.cgitsync`, which stay unchanged. They are declared in an operator TOML file
named by `ATCGS_MOUNTS`:

```toml
[[mount]]
name = ".omniscience"         # PUBLIC, must be read-only
repository = "github:<owner>/<public-repo>"
ref = "main"
commit = "<full 40- or 64-hex commit id>"
policy = "PUBLIC"

[[mount]]
name = ".computo"             # PRIVATE, OPX/DEV with ATCGS_AUTHORIZE only
repository = "github:<owner>/<private-repo>"
ref = "main"
commit = "<full commit id>"
policy = "PRIVATE"
writable = true
```

Refused: any name other than `.omniscience`/`.computo`, a policy that differs
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
- The dependency is fixed to a reviewed CGS-ALPHA commit; no unlocked branch
  update can silently replace its invariants.
- `pixi.lock` must be generated and committed during integration on a host
  with Pixi and Git network access; it is not fabricated here.
- Test `release freeze` in a disposable GitTree before permitting pushes to a
  production project. Even an accepted request can still fail safely inside
  `cgitsync` because of workspace/integrity/permission guards.
- This is a **breaking `@cgs` API change** (raw verbs → selectors) for `@cgs`
  callers only; ComplexGitSync state requires no migration.

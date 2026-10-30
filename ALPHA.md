# @cgs — minimal ALPHA entry point

The `@cgs` name is simultaneously a **Pixi task** and a **Python decorator**.
Its `OpFrontier` accepts a small, explicit command surface, then calls
`ComplexGitSync.cli.main` with the exact original arguments. The existing
CGS-ALPHA CLI routes mutating operations via `RoutedClient -> Op`.

```bash
pixi install
pixi run '@cgs' --version
pixi run '@cgs' bootstrap example.cgs
# Configure CGSHOME using the output of bootstrap.
pixi run '@cgs' status
pixi run '@cgs' release freeze "ALPHA release" --dry-run
# Explicit operator approval is required before an actual freeze/push/tag:
pixi run '@cgs' release freeze "ALPHA release"
pixi run '@cgs' release list
pixi run test
```

- `@cgs` does **not** create or verify Merkle roots, `.gts` proofs or PoE.
- It does **not** implement CGS-BETA, GX4G or `*G` requestability.
- PRIME G is `{NAME, NODE, EDGE, OP*}`. The ALPHA adapter does not copy CGS-BETA frontier tuples or introduce GitRepo mounts or `.cgs` grammar. Existing CGS-ALPHA `Op` remains authoritative.
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

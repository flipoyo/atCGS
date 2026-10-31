# Short ticket: cgs naming and conformity

Owner's request, 2026-10-31. Related: f6eca7e, opx-agentic-mounts.md.

The project is named cgs. cgitsync and @cgs are two names for the same
build executable in the Pixi environment (.pixi/envs/default). Make the
repository conform to that.

Conformity:
- Commit subject: cgs-<version>, as in cgs-0.1.1-alpha. f6eca7e used
  POEX-0.1.1-alpha and does not conform; amend it before pushing.
- Executable: the pixi task @cgs and the cgitsync command name the same
  build. Document both in ALPHA.md and do not name a third one.
- Project name in .cgs files: project = { name = "POEX" } in POEX.cgs and
  examples/cgs-{opx,dev,usr}.cgs. Under this rule it should be "cgs", unless
  the owner keeps POEX as the install name (open point).
- Branch POEX and the POEX.0000 ontology stay unchanged.

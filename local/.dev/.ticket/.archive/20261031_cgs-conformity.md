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

Closed 2026-10-31:
- Commit subjects: f6eca7e and 4f35cbe are on origin/main and origin/CGS-ALPHA;
  accepted, not amended. Subjects now come from atcgs.commit_subject().
- Executable: ALPHA.md documents @cgs and cgitsync as two names of one build.
- Project name: cgs in POEX.cgs and the layer trees, on CGS-ALPHA, fallback main.
  The layer files are renamed cgs_{opx,dev,usr}.cgs: ComplexGitSync reads
  cgs-<xxx>.cgs as a contract asking for branch <xxx> and fallback CGS-BETA.
- Writable private repos of the DEV tree take the computed branch cgs_CGS-ALPHA
  instead of POEX. Branch POEX and the POEX.0000 ontology are untouched, but
  DEV no longer writes branch POEX; the OPX tree reads cgs_CGS-ALPHA too (owner's yes).

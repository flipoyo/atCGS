# Short ticket: mount the OPX register

Owner's decision, 2026-10-31 (poex-open-points, point 9): OPX persists the
register NAME -> (hash(SEED), hash(GLYPH)) in a private repository mounted
only by the OPX tree, writable there, like ComplexGitSync's .cgitsync/.memory.

Done in 1.4.0-alpha: atcgs.Register persists the register in the JSON file
named by ATCGS_REGISTER, and `@cgs <LAYER> prove` reads it.

To do:
- Name the repository (e.g. github:flipoyo/.register, private) and create it.
- Mount it in examples/cgs_opx.cgs only, private and writable, e.g. at
  .cgitsync/.register, and point ATCGS_REGISTER at its file.
- tests/test_layers.py: the register is mounted at OPX and nowhere else.

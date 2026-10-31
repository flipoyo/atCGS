# Short ticket: finalise POEX — split poex (comparison) and eopx (birth)

Owner's request, 2026-10-31, on branch CGS-ALPHA after bdf77fa.
Related: cgs-conformity.md, opx-agentic-mounts.md.

Two microcodes, two purposes:
- poex, Proof of Existence: its only purpose is comparison.
- eopx, Existence of Proof: the birth protocol, the registration of a
  NAME with the compression algorithm.

bdf77fa puts the birth protocol in atcgs.POEX (integrate, compress) and
uses poex only to frame the GLYPH. Move it where it belongs.

To do:
- poex.c: make comparison its only purpose. Proposal: POEX feeds it
  GLYPH_A XOR GLYPH_B and the GLYPHs are equal if and only if
  zeros = 65536. Neither GLYPH leaves POEX.
- atcgs.POEX: compare two unknown GLYPHs, both rebuilt internally by POEX
  from SEEDs, then check them with poex. Drop integrate() and compress().
- eopx: new microcode for the birth protocol. A square SEED .bit of at least
  256x256 bits; compressed to a 256x256 GLYPH, deterministically, from the
  initial value hash(SEED); always compressed, so hash(GLYPH) != hash(SEED);
  hash(SEED) must be a unique ID; NAME -> (hash(SEED), hash(GLYPH)) known by
  OPX only.
- Python wrapper for eopx, alongside POEX.
- Contract, README, TUTO 05 and microcode/README.md: describe both microcodes.
- Tests: poex compares, eopx gives birth, and the GLYPH is never stored.

Open points, not decided here:
- Where do POEX's two GLYPHs come from? Only hashes are stored, so each GLYPH
  must be rebuilt from a SEED someone presents: X and X.poe in one request,
  or one SEED from each side of the OpFrontier.
- eopx in C needs shake_256 (Keccak). No C standard library has it: write it
  in the monolithic microcode, link a library, or keep the compression in
  Python and let eopx only frame and count.
- Where OPX persists the register NAME -> (hash(SEED), hash(GLYPH)).
- KEY: [key] says holder = POEX, but the pair is now OPX only.
- Public boundary: the chain breaks after README atCGS USR PUB (next is GLYPH)
  and after HASH DELTA CGS OPX (next is .cgs). Keep both rows or drop them?
- microcode/README.md:42 lets .cgitsync handle .bit bytes, which conflicts
  with the GLYPH never being exposed.
- Pixi: cc and ssh-keygen come from the system; add a C compiler and openssh?
- No @cgs selector calls POEX yet.
- 1.0.0-alpha: .computo is now .cgitsync (ComplexGitSync); the Operating Space reads
  .omniscience and .cgitsync. Still open: whether .agent becomes a third space
  of the contract (the trees mount it, the contract does not name it), and
  POEX.0000.toml, whose .opx frontier still says .computo (left unchanged).

Closed 2026-10-31 (1.1.0-alpha):
- poex.c compares only: stdin is GLYPH A then GLYPH B; equal iff zeros = 65536;
  exit 0 equal, 1 different, 2 bad size.
- eopx.c: new monolithic microcode, SEED -> GLYPH with SHA-256 and SHAKE-256
  written in C, checked against hashlib on every reachable padding case.
- atcgs.EOPX wraps eopx (glyph, birth); atcgs.POEX wraps poex (exists,
  compare, poe). integrate(), compress() and seed_side() are gone.
- Contract [poex] purpose and [eopx] section, checked by contract_check.
- microcode/README.md, README and TUTO 05 describe both microcodes;
  microcode/README.md:42 no longer lets .cgitsync handle GLYPH bytes.
- The remaining open points move to poex-open-points.md.

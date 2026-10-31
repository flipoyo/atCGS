# Short ticket: POEX / EOPX open points

Carried over from poex-eopx-finalise.md (archived 2026-10-31, 1.1.0-alpha).
Related: microcode/README.md, atcgs.POEX, atcgs.EOPX.

Open points, not decided here:
- Who presents the two SEEDs that POEX.compare(seed_a, seed_b) rebuilds:
  X and X.poe in one request, or one SEED from each side of the OpFrontier.
  The class takes both; no caller does yet.
- Where OPX persists the register NAME -> (hash(SEED), hash(GLYPH)). The OPX
  tree now mounts codeberg:GX4G/.omniscience writable, but .omniscience is
  PUBLIC and the pair is OPX only.
- KEY: [key] says holder = POEX, but the pair is OPX only.
- Public boundary: the chain breaks after README atCGS USR PUB (next is GLYPH)
  and after HASH DELTA CGS OPX (next is .cgs). Keep both rows or drop them?
- Pixi: cc and ssh-keygen come from the system; add a C compiler and openssh?
- No @cgs selector calls POEX or EOPX yet.
- Whether .agent becomes a third space of the contract (the trees mount it,
  the contract does not name it).
- POEX.0000.toml: its .opx frontier still says .computo (left unchanged).
- USR: the cgitsync message asked for .agent/.local writable at every level;
  the USR tree mounts nothing private, so USR has none.
- .poe ladder (1.2.1-alpha): POE 0000, OPX 0000, DEV 1000, USR 1100, PUB 1111.
  OPX only through POE: OPX is EOPX. Session.prove gives birth to an unknown
  NAME from left, then 0000 for left = right, 1111 for left != right, and 1000
  for a failed control (assumed from the earlier "mismatch goes to DEV" flow;
  owner to confirm). No case gives 1100 (USR) yet.
- Naming: .poe is now the 4-bit decorator, but PoeVector, the 4 x 256-bit
  credential vector returned by POEX.poe(), is also called .poe in the docs.

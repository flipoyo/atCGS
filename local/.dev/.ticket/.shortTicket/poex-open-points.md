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
- Public boundary: the chain breaks after README atCGS USR PUB (next is GLYPH)
  and after HASH DELTA CGS OPX (next is .cgs). Keep both rows or drop them?
- No @cgs selector calls POEX or EOPX yet.
- Whether .agent becomes a third space of the contract (the trees mount it,
  the contract does not name it).
- .poe (1.2.2-alpha), settled by the owner: POEX knows who asks and only asks
  whether poe can be granted. Granted is 0000; refused keeps the requester's
  code, OPX 1000, DEV 1100, USR 1110, PUB 1111. Assumed from "OPX is EOPX":
  only an OPX requester gives birth to an unknown NAME.

Closed 2026-10-31 (1.3.0-alpha), owner's answers:
- KEY: [key] holder = "OPX".
- POEX.0000.toml: removed, with its pinning test.
- USR stays private-free: no .agent/.local at USR (answer for the cgitsync side).
- Pixi: c-compiler in [dependencies], openssh in [target.unix.dependencies]
  (conda-forge has none for win-64); cc and ssh-keygen now come from Pixi.
- Naming: the 4 x 256-bit vector is .cred (atcgs.Cred, POEX.cred()); .poe is
  only the 4-bit decorator.

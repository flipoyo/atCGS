# Short ticket: OPX agentic mounts and cgs-opx.cgs

Source: owner request on 2026-10-31, after cgs-0.1.1-alpha on main (commit 37c7e81).
Related: atCGS #2 (closed), POEX.cgs, examples/cgs-{opx,dev,usr}.cgs.

Mount the OPX agentic structure of ComplexGitSync in .agent/.distant and
.agent/.local, following complexgitsync-opx.cgs. Write cgs-opx.cgs from it.

Owner's description of the .omniscience record, to be carried into the
specifications and checked against the code:
- .omniscience holds hash(timestamp), hash(NAME), hash(.gts), hash(install.cgs), hash(.toml).
- hash = sha256 of a Python object.
- .cgs and .gts are organised in .omniscience and connected to .computo through hash(NAME).

Open points, not decided here:
- ComplexGitSync's record hash (omniscience_record.py, merkle_root.py) does not
  match this. It excludes recorded_at and every who/when field so that the same
  registration is always the same file, uses tagged canonical hashing, not
  sha256 of a Python object, and does not hash install.cgs.
- AdditionalSpecs.md, "The Omniscience register", is the authority for the record.
  Decide whether atCGS keeps that definition or adds a POEX-specific one.
- A new hash implementation is out of scope for atCGS (see #2).

# Short ticket: the published identities move from CGS-MOLO to main

Source: MolonariCgsMolo (archived 2026-11-05), decision D2: *"yes in theory but
create a CGS-MOLO for use until we validate the development"*.

Today `@cgs OPX publish` writes `atcgs/identity.jsonl` and `atcgs/identity.head`
on branch `CGS-MOLO` of `flipoyo/omniscience`, and `examples/molonari.cgs`
mounts `.omniscience` read-only on `CGS-MOLO`.

To do, once the owner validates the development:
- Promote `CGS-MOLO` to `main` of `.omniscience` (`@cgs OPX login … promote
  .omniscience CGS-MOLO main` from a tree that mounts it writable, or merge if
  `main` has moved).
- `atcgs.commands.PUBLISH_BRANCH = "main"`; `molonari.cgs` mounts
  `.omniscience` on `main`; the tests follow.
- Re-run `pixi run cgs OPX publish`, then `pull` the MOLONARI tree.

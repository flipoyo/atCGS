# Short ticket: close the public boundary into one loop with curl

Owner's decision, 2026-10-31 (poex-open-points, point 4): a ComplexGraphSync
curl operation closes the public boundary into one loop. It is git interaction
with a forge CLI: gh (GitHub), glab (GitLab) or tea (Gitea/Forgejo, Codeberg).

1.5.0-alpha removes the unnecessary GLYPH row (owner: "GLYPH can go away").
The four rows still break twice:
  README atCGS USR PUB      ends PUB,  next starts DELTA
  DELTA POEX OPX HASH
  HASH DELTA CGS OPX        ends OPX,  next starts .cgs
  .cgs USR PUB .toml

To do:
- Owner: name the two connecting tuples, PUB ... DELTA and OPX ... .cgs.
- Define the closing edge .toml -> README as curl, and which forge CLI it
  calls for which host (github, gitlab, codeberg).
- Add the rows to spec/contracts.toml and contract_check; publication stays
  NOT_PUBLISHED until a real checkpoint exists.

# Short ticket: close the public boundary into one loop with curl

Owner's decision, 2026-10-31 (poex-open-points, point 4): a ComplexGraphSync
curl operation closes the public boundary into one loop. It is git interaction
with a forge CLI: gh (GitHub), glab (GitLab) or tea (Gitea/Forgejo, Codeberg).

Today the five rows break twice:
  README atCGS USR PUB      ends PUB,  next starts GLYPH
  GLYPH POEX PUB DELTA
  DELTA POEX OPX HASH
  HASH DELTA CGS OPX        ends OPX,  next starts .cgs
  .cgs USR PUB .toml

To do:
- Owner: name the two connecting tuples, PUB ... GLYPH and OPX ... .cgs.
- Define the closing edge .toml -> README as curl, and which forge CLI it
  calls for which host (github, gitlab, codeberg).
- Add the rows to spec/contracts.toml and contract_check; publication stays
  NOT_PUBLISHED until a real checkpoint exists.

# Short ticket: GitHub deploy keys and the journals' distribution

Source: IdentityJournals (archived 2026-11-03), M7 and its open points.

To do:
- M7: on `OPX admit` and `OPX revoke`, install or remove the grant's ssh public
  key as a GitHub deploy key (`gh api repos/{owner}/{repo}/keys`): write for
  DEV, read-only for USR. `scripts/local_remote.py` is the local model of it.
  GitHub refuses a deploy key already used on another repo; the GLYPH already
  holds one key per (repo, role).
- Pin OPX's key: the owner runs `ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX init`
  and copies `idpub` into `spec/contracts.toml [identity] opx_pub`.

Open points, not decided here:
- DEV and USR need the journals to log in, but the register is mounted at OPX
  only. Options: publish identity.jsonl in `.omniscience` and hand each user
  their own signed grants; or mount a read-only copy of the register at DEV/USR.
- Projecting the identity journal and both chain heads to `.omniscience`.
- `@cgs <LAYER> rotate` (password change) exists in the API (`Register.rotate`)
  but not as a command; it also needs the GLYPH resealed under the new key.

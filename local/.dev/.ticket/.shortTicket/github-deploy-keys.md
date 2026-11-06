# Short ticket: GitHub deploy keys and the journals' distribution

Source: IdentityJournals (archived 2026-11-03), M7 and its open points.

To do:
- 2026-11-06: the install side of M7 is done for onboarding: `OPX onboard` installs the deploy keys with `gh`
  (idempotent, after the plan and one `y`; archived OwnerOnboarding). Not done: removal on `OPX revoke`
  (the planned `offboard`), and installing from `OPX admit` alone.
- M7: on `OPX admit` and `OPX revoke`, install or remove the grant's ssh public
  key as a GitHub deploy key (`gh api repos/{owner}/{repo}/keys`): write for
  DEV, read-only for USR. `scripts/local_remote.py` is the local model of it.
  GitHub refuses a deploy key already used on another repo; the GLYPH already
  holds one key per (repo, role).
- ~~Pin OPX's key~~: done 2026-11-05 (Dogfooding).
- `pixi run deploy-keys --repo github:o/n` prints only the named repositories
  (MolonariCgsMolo); the owner still runs the printed `gh api` commands.

Open points, not decided here:
- DEV and USR need the journals to log in. Since 2026-11-03 the register is
  `.cgitsync/.memory/.register` (the project's own memory), mounted at OPX only.
  Options: mount `.cgitsync/.memory` read-only at DEV (USR stays without it), or
  project identity.jsonl plus each user's own signed grants to them.
- ~~Projecting the identity journal to `.omniscience`~~: done (`OPX publish`,
  MolonariCgsMolo); projects copy it into their own register. The access
  journal stays per project.
- `@cgs <LAYER> rotate` (password change) exists in the API (`Register.rotate`)
  but not as a command; it also needs the GLYPH resealed under the new key.

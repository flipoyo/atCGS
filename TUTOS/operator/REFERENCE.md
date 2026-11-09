# atCGS reference — for operators and developers

*The user-oriented introduction is the [README](../../README.md). This file is the
technical reference it used to hold: what runs, how sessions and the identity work,
what is not built, and where everything lives. Section numbers are kept stable;
code and specs cite them as `REFERENCE.md § N`.*

## 1. Development quick start

Everything runs under Pixi, from the repository root.

```bash
pixi install
pixi run test              # the atCGS suite (tests/)
pixi run lint
pixi run contract-inspect  # checks spec/contracts.toml against the code
pixi run identity-demo     # the identity flow on throwaway data; 4 refusals are shown
pixi run local-remote      # the same against a local sshd (needs sshd and git-shell)
pixi run cgs --help
```

```

One command, `pixi run cgs …`, over two manifests:

| Manifest | ComplexGitSync | Used where |
|---|---|---|
| `pixi.toml` | pinned (git rev) | any install of atCGS, a project's read-only gate (`.atcgs`) included |
| `@cgs/pixi.toml` | `./ComplexGitSync`, editable | the development Operating Space, where atCGS and ComplexGitSync are developed together |

`pixi run cgs` (`scripts/cgs.py`) hands over to `@cgs/pixi.toml` wherever `./ComplexGitSync`
is checked out, and runs atCGS on the pinned ComplexGitSync anywhere else; `ATCGS_PINNED=1`
keeps the pinned one. The root manifest never names `./ComplexGitSync`, so a clone without it
installs with a plain `pixi install`. The other tasks of `@cgs/` run with `-m`
(`pixi run -m @cgs test`). A test keeps the two manifests equal but for the ComplexGitSync source
and the `cgs` task.


## 2. What runs today

| Capability | How to run it | Checked by |
|---|---|---|
| Four levels and their codes, taken from ComplexGitSync | `pixi run cgs OPX` (or `DEV`, `USR`, `PUB`) | `test_layers`, `test_atcgs` |
| OpFrontier transitions `.gts OPX DEV .cgs`, `.cgs DEV USR .toml`, `.toml USR PUB .omniscience` | `pixi run cgs DEV` | `test_atcgs`, `contract-inspect` |
| Identity key from login and password (Argon2id, Ed25519) | `@cgs … request`, `@cgs … login` | `test_identity_layer` |
| Journals: who exists, and who holds which role on which repo | `@cgs OPX init`, `admit`, `revoke` | `test_identity_layer` |
| GLYPH: a user's ssh keys sealed in 8 192 bytes, growing x4 when full | `@cgs … request` | `test_identity_layer` |
| Session: keys in a private ssh-agent, one key per repo, never `~/.ssh` | `@cgs DEV login TWIN <op>` | `test_identity_layer`, `local-remote` |
| Workspace tree `examples/cgs-alpha.cgs` (project `cgs`, branch `CGS-ALPHA`) | `pixi run cgitsync validate examples/cgs-alpha.cgs` | `test_layers` |
| Workspace tree `examples/ComplexGraphSync.cgs` | `pixi run cgitsync validate examples/ComplexGraphSync.cgs` | `test_layers` |
| GitHub deploy keys as commands (printed, not run), all or per repo | `pixi run deploy-keys [--repo github:o/n]` | `test_identity_layer` |
| Identities published to `.omniscience` (branch `CGS-MOLO`) from a throwaway worktree | `@cgs OPX publish` | `test_project_register` |
| A read-only atCGS serves the register of the project that mounts it; identities are copied, grants stay local | `@cgs OPX login TWIN <op>` inside a project tree | `test_project_register` |
| The MOLONARI twins, each with atCGS as its gate: MOLO-HRDW, MOLO-DATA, MOLO-CMPT, MOLO-TWX | `pixi run cgitsync validate examples/molo_twx.cgs` | `test_layers` |
| Enrol an identity in the master register only, no grant | `@cgs OPX enrol REQUEST` | `test_project_register` |
| A session also loads its UID's read-only USR grants (a DEV reads a twin's gate) | `@cgs DEV login TWIN <op>` | `test_project_register`, `test_identity_layer` |
| One repository's branch fast-forwarded on its remote (CGS-ALPHA → main), never forced | `@cgs OPX login TWIN promote DIR FROM TO` | `test_project_register` |

## 3. Levels

atCGS does not define its levels. It imports them from ComplexGitSync
(`ComplexGitSync/src/ComplexGitSync/orchestre/op_levels.py`). A level's code is its
four-bit vector over (NAME, NODE, EDGE, OP):

| Level | Code | Exposes | Meaning |
|---|---|---|---|
| OPX | `0000` | nothing | maintainer; OPX is POE |
| DEV | `1000` | NAME | developer |
| USR | `1100` | NAME, NODE | reviewer |
| PUB | `1111` | all four | public projection |

PUB is the absence of a grant. A UID with no grant on a repo is PUB on that repo.

There is no level tree and no level branch: the whole alpha series is on `CGS-ALPHA`, and the one
workspace file is `examples/cgs-alpha.cgs`. What a DEV or a USR gets is the role template of
`request --register`.

## 4. The BIOS declaration

The BIOS is a **declaration**. Nothing reads it at start-up, and no code boots from it.
`pixi run contract-inspect` checks its form against `spec/contracts.toml`: each row
must match the fixture in `scripts/contract_check.py`, in the same order.

| Section of `spec/contracts.toml` | Rows | What it is |
|---|---|---|
| `[boot] identity` | 1 | `atCGS ALPHA BIOS ComplexGitSync M.m.p`: the name, and the engine version to pin. `M.m.p` is a placeholder; no installed version is claimed. |
| `[boot] current` | 5 | The boot chain in force (below). |
| `[bios_history]` | 7 rows, plus 2 `extensions` | Earlier BIOS rows, kept as written. Checked for form only. |

The five rows of `[boot] current`:

```text
ComplexGitSync G POEX .gts
.gts G OPX TWX
TWX ENV HWX DEV
DEV HWX TWX USR
USR TWX G .cgs
```

Reading the symbols:
- `G`, `.gts`, `.cgs`, `OPX`, `DEV`, `USR` name things this software uses.
- `ENV`, `HWX`, `TWX` are placeholders. Nothing implements them yet.
- `POEX` in the first row is kept as written. The POEX microcode was removed in
  1.6.0 (§ 7), so this row names a component that no longer exists.

## 5. Sessions and commands

Run each command as `pixi run cgs <LAYER> ...`.

| Command | Effect | Who may run it |
|---|---|---|
| `OPX init [PROJECT] [--plan] [--from PATH]` | Makes this machine OPX, from any state, in one run: a new atCGS pins the key (`spec/opx.toml`, append only), enrols, makes and grants the workspace's keys, installs the deploy keys, pushes; a pinned machine without a GLYPH rebuilds it (`--from` takes a copy); `PROJECT` makes the Owner OPX of that project, reusing the keys the GLYPH holds. Refuses another login once a key is pinned, and an atCGS behind `origin/CGS-ALPHA`. | OPX, with `ATCGS_AUTHORIZE=OPX` |
| `<LAYER> request OUT REPO ROLE …` | Generates one ssh key per repo, seals them in the user's GLYPH, and writes `OUT` with the public keys and the proof. | any user |
| `<LAYER> request --register P=R [--name N] OUT.toml` | The same for whole projects: the repositories come from the project's `.cgs` and the role template (atCGS and omniscience are USR). `OUT.toml` is the registration file for the Owner. | any user |
| `<LAYER> user-credential [--json] [--probe] [--tree PATH]` | Reads your GLYPH (keys, fingerprints, room), every register under `~/.cgs` (or `--tree`) that knows your uid, and gives a verdict per (repository, role): `ok`, `no key`, `not admitted`, `revoked`, `refused by GitHub` (`--probe`). Read only. Exit 0 when every grant is `ok`. | any user |
| `<LAYER> generate-glyph [--from PATH] [--tree PATH]... [--out FILE] [--plan]` | Gets a GLYPH back. `--from` takes a copy that opens with this login. Otherwise keeps the keys the GLYPH has that match a grant and makes new ones for the rest; the atCGS OPX then rekeys the registers (`Register.rekey`), installs the new deploy keys, pushes the registers and deletes the old deploy keys; anyone else gets a request file for `OPX admit`. A repository gone from GitHub gets no key and its grants are revoked. | any user |
| `OPX intake [FOLDER]` | Verifies every registration file of `~/.cgs/registration/` (or `ATCGS_REGISTRATION`) and writes the day's list in `~/.cgs/intake/` (or `ATCGS_INTAKE`). No password. | OPX |
| `OPX onboard LIST [--plan]` | For the confirmed persons of the list: enrol, publish, pull `.omniscience` in each project tree, admit, install the deploy keys with `gh`, commit and push the register alone. One password prompt. `--plan` writes nothing. | OPX, master register |
| `OPX enrol OUT` | Enrols the user only, in the master register; grants nothing. | OPX, master register |
| `OPX publish` | Copies the master `identity.jsonl` to `.omniscience/atcgs/` (branch `CGS-MOLO`). | OPX, master register |
| `OPX admit OUT` | Enrols the user if new (master register only), then grants each requested repo and role in this project's register. | OPX |
| `OPX revoke UID [REPO]` | Revokes a UID (master register only), or one grant (any register). | OPX |
| `<LAYER> login TWIN [op …]` | Opens a session and runs `cgitsync op …` through it. | by grant |

`login` allows these cgitsync operations per level (`atcgs/__init__.py`, `LOGIN_OPS`):

- USR: `status`, `view-tree`, `fetch`, `pull`, `validate`.
- DEV: the USR list, plus `add`, `rm`, `commit`, `push`, `branch`, `checkout`, `merge`, `autofix`.
- OPX: the DEV list, plus `tag`, `release`, `bootstrap`, `initialise`, `omniscience`,
  `memory`, `promote`, `env`, `verify`, `unlock`, `self-history`.

"OPX" in the table above (`enrol`, `publish`, `admit`, `revoke`, `init`) means **atCGS OPX**:
the login and password whose key is pinned in `spec/contracts.toml`. There is one. A UID
granted the role `OPX` in a project runs that project's OPX `login` operations, but every
register line is signed by the pinned key, so it cannot admit or revoke.

**Selectors.** `@cgs` accepts four selectors, `OPX`, `DEV`, `USR`, `PUB`; anything else exits
with code 2. With no argument a selector prints its OpFrontier transition (`.gts OPX DEV .cgs`,
`.cgs DEV USR .toml`, `.toml USR PUB .omniscience`; `"evidence"` is always `unverified`).
A bare cgitsync verb (`@cgs DEV status`) or a private mount (`@cgs DEV .cgitsync`) needs
`ATCGS_AUTHORIZE`, which may name only `OPX` and/or `DEV`; so do `init`, `enrol`, `admit`,
`revoke` and `publish`. `request` and `login` do not. Mounts resolve from `ATCGS_MOUNTS`
(a TOML of `[[mount]]` with pinned commits); without it they answer `"evidence": "unavailable"`.

Anything else is refused. `login` writes `TWIN.cgs` only for a bare login or for
`bootstrap`/`initialise`, never inside a tracked repository.

**Onboarding** (`atcgs/registration.py`, `atcgs/onboard.py`). `onboard` runs in the workspace and acts on a
project tree by setting `ATCGS_PROJECT` and `CGSHOME` to it for the length of each step (restored after);
`ATCGS_PROJECT` is read by `project_root`, so the register, the published identities and the `login` check
are those of that tree. Project trees are found in `ATCGS_TREES` (default `~/.cgs`), newest
`<PROJECT>-*` first, unless the list names one. It reads the Owner's login and password once and passes the
identity down; every step is repeatable. Only `.cgitsync/.memory/.register` is committed, and a tree whose
memory has other changes is refused. The cgitsync memory fold is not run: the register commit is a plain git
commit on the memory branch the tree is on.

A session runs these steps in order (`atcgs/session.py`):
1. Recomputes the UID from the typed login and password. Nothing is looked up.
2. Checks the identity journal: the UID is enrolled and not revoked.
3. Proves possession: the UID's key signs a fresh challenge, which is verified.
4. Reads the access journal: the repos where the UID holds this level.
5. Opens the GLYPH and matches each granted repo by ssh fingerprint.
6. Starts a private `ssh-agent` in a 0700 directory and loads only those keys.
7. Runs the command with `GIT_SSH_COMMAND` pointing at a wrapper. The wrapper offers
   each repo its own key, and never `~/.ssh` (`-F /dev/null`).
8. Empties the agent, kills it and removes its directory, also when a step fails.

## 6. Identity, journals and GLYPH

- **Identity.** `IDSEED = Argon2id(password, "atCGS/id/v1/<profile>/<login>")`, from
  which an Ed25519 key pair is derived. `UID = sha256(IDPUB)`. The profile `real` uses
  256 MiB and 3 passes; `test` is used by the suite (`ATCGS_KDF_PROFILE=test`).
  Login and password are Unicode-normalised (NFC) first. The OPX key is pinned in `spec/opx.toml` (`atcgs.pin`): append-only `[[pin]]` blocks, the last in force; the older pin of `spec/contracts.toml [identity] opx_pub` is read only when there is none.
- **Journals.** `identity.jsonl` (enrol, rotate, revoke) and `access.jsonl` (grant,
  revoke) live in the register: `.cgitsync/.memory/.register`, or the directory that
  `ATCGS_REGISTER` names. Each line is signed and chained by `prev = sha256(previous
  line)`. Reading refuses the whole file at the first fault.
- **Project registers.** The register belongs to the project that holds atCGS: the nearest
  directory at or above atCGS with a `.cgitsync/`. Where atCGS is the project's root it is the
  *master* register, the only one that enrols and revokes identities. Where atCGS is a read-only
  mount (`.atcgs` in `examples/molo_*.cgs`), the register is that project's own: `@cgs OPX publish`
  copies the master `identity.jsonl` to `.omniscience/atcgs/` (branch `CGS-MOLO`, then `main`) and
  every `login`/`admit` of a project copies it into its register, verified against the pinned OPX
  key. A project register that holds a line the published copy lacks is refused, never merged.
  Identity is global; `access.jsonl` is local to the project. `login` refuses when `CGSHOME` names
  another tree.
- **GLYPH.** 8 192 bytes at level 0 (`GLYPH_BYTES`); each further level is 4 times larger (32 KiB, 128 KiB, ... up to level 4), chosen by `seal` as the smallest the keys fit in, never smaller than the GLYPH it replaces, and read back from the file length. Level 0 layout: `"CGSG" | version | nonce | ChaCha20-Poly1305 ciphertext | tag`,
  keyed by HKDF of the IDSEED. It holds the user's private ssh keys, one per (repo, role),
  zero-padded to a fixed length. Without the login and password it is noise, and one
  flipped bit makes it refuse. It is written to `~/.cgs/.glyph/<UID>.glyph`
  (`ATCGS_GLYPHS` overrides the folder).
- **Deploy keys.** `pixi run deploy-keys` prints one `gh api` command per active GitHub
  grant. It runs nothing.

The access journal reveals which UIDs work on which repos, so it stays private. Only
the identity journal and the access chain head may be projected to `.omniscience`,
and that projection is not built (§ 8).

## 7. Removed in 1.6.0: POEX and EOPX

Version 1.5.0-alpha had two C microcodes, `poex` (XOR zero count of two GLYPHs) and
`eopx` (SEED to GLYPH), the `@cgs … prove` verb, and a 4×256 packet simulator. They are
removed. Their last state is commit `4e3ec5e` (subject `cgs-1.5.0-alpha`); no tag exists for it.

They were replaced because the 1.5 GLYPH was derived from a secret, so proving an
identity meant sending that secret. The 256×256-bit size survives as the GLYPH size.
The 4-bit codes survive as the level codes of § 3.

## 8. Not implemented yet

- **USR login is not proven on a real tree.** A DEV was registered and worked on MOLO-HRDW
  on 2026-11-05 (TUTOS 01-03); no USR has logged in to a real twin yet.
- **On one machine, a commit's author is the machine's git identity,** not the session's UID:
  atCGS decides who may push, it does not sign commits.
- **`login` runs the level's command only for a bare `bootstrap`.** Any other verb
  runs as given on the command line.
- **Deploy keys are not installed.** `deploy-keys` prints them; M7 would run them.
- **One-line commit messages.** `@cgs … commit` keeps only the first line.
- **The projection is `identity.jsonl` only.** `.omniscience` holds no hash record (short ticket
  opx-agentic-mounts) and no chain head beyond `atcgs/identity.head`.
- **A DEV's `.memory` key opens the whole memory repository.** It is a deploy key of
  `flipoyo/.memory`, which holds every twin's memory branch; registers are signed, so a
  tampered one is refused, but other branches can be written.
- **A twin copies identities from its local `.omniscience` checkout:** after `OPX publish`,
  `pull` the twin before `admit`, or the new identity is not there yet.
- **No `'` in a commit message:** pixi quotes task arguments with single quotes and does not
  escape them.
- **No version tag.** Releases are identified by the commit subject (`cgs-<version>`); no tag is created.

## 9. Repository layout

| Path | Contents |
|---|---|
| `atcgs/` | the package: `identity`, `journal`, `glyph`, `session`, `commands`, `registration`, `onboard`, `credential`, `glyphgen`, `ownerinit`, `pin`; the `@cgs` entry point in `__init__` |
| `spec/contracts.toml` | the BIOS, frontier, identity and GLYPH rows that `contract-inspect` checks |
| `examples/cgs-{opx,dev,usr}.cgs` | the three level trees, named by level (§ 3) |
| `examples/ComplexGraphSync.cgs` | the workspace tree this repository is developed in |
| `POEX.cgs` | the PUB install: the public root and nothing private |
| `scripts/` | `contract_check.py`, `identity_demo.py`, `local_remote.py`, `deploy_keys.py` |
| `tests/` | the suite; `pixi run test` runs only these |
| `TUTOS/` | the two tutorials (operate a project; omniscience) and this reference |

`.cgitsync/` and `.omniscience/` are mounts of the workspace tree. They are not part
of this repository's history.

## 10. Tracking

- ComplexGitSync #193: https://github.com/flipoyo/ComplexGitSync/issues/193
- atCGS #2: https://github.com/flipoyo/atCGS/issues/2
- atCGS PR #1: https://github.com/flipoyo/atCGS/pull/1
- Open planning tickets are in `local/.dev/.ticket/openTickets/` and are not published.

## 11. Operating a project: the details behind TUTO 1

### `gh` and deploy keys

`gh` comes with `pixi install`; atCGS uses it, and only it, to install deploy keys. An ssh key signs
`git push`/`git pull`; adding a deploy key is a GitHub API call that needs a token with admin rights on
the repository. `gh auth login --git-protocol ssh --web` stores that token in `~/.config/gh` (shared with
any other `gh`). `GH_TOKEN=<token>` in front of a command does it for one run. A missing or logged-out
`gh` is listed under `problems` and the run stops before asking anything.

### `OPX init`: what it does, by machine state

It asks login and password (twice when the key is new), prints a plan, asks `Apply this plan? (y/N)`.
Run again, it changes nothing.

| The machine is | `OPX init` does |
|---|---|
| a new atCGS, no key pinned | installs the workspace if missing (`cgitsync bootstrap examples/cgs-alpha.cgs`, https); makes the key and pins it in `spec/opx.toml`; enrols it in the master register; one ssh key per repository, sealed in the GLYPH; OPX grants; deploy keys on GitHub; commits and pushes pin and register; publishes the identities |
| another machine, already OPX | rebuilds the GLYPH for the access already held (`--from PATH` reuses a copy; otherwise new keys, registers and GitHub updated, old deploy keys removed last). Never enrols again |
| everything in order | prints the `user-credential` table, changes nothing |
| a key pinned, another login | refuses: there is one OPX |

*Pinning* appends the public key to `spec/opx.toml` (earlier blocks stay as history) and pushes it, so every
gate knows who the Owner is: a register line is trusted only if signed by that key. The master register,
`.cgitsync/.memory/.register/identity.jsonl`, is the only place where people are enrolled; project
registers copy it. `init` refuses from an atCGS behind `CGS-ALPHA` (`git pull` first). A push of atCGS
itself is refused while `pixi run test` fails (`ATCGS_SKIP_TESTS=1` skips it).

`OPX init PROJECT` installs the project tree when there is none (as `cgitsync bootstrap` would), grants
OPX on every repository of its `.cgs`, reuses the GLYPH keys already held for the same repository and
role (atCGS, omniscience and `.memory` are shared with the workspace), installs the new deploy keys and
pushes the project register.

### `user-credential`

Read-only; one password. Prints the uid, the GLYPH fill, each register, then one row per repository and
role:

| Verdict | Means | Do |
|---|---|---|
| `ok` | granted, key in the GLYPH | nothing |
| `no key` | granted, key not in the GLYPH (or `glyph MISSING`) | `OPX init` / `generate-glyph` |
| `not admitted` | key in the GLYPH, granted nowhere | `admit` it, or ignore |
| `revoked` | identity revoked | ask the Owner |
| `refused by GitHub` | with `--probe`: deploy key not on GitHub | `OPX init` installs it again |

`--probe` runs one `git ls-remote` per key through the session; `--json` prints data; `--tree PATH`
reads one tree. Exit 0 when every grant is `ok`. `OPX onboard` runs it first and stops if the GLYPH is
missing or a memory/omniscience grant has no key.

### A lost GLYPH

Private keys exist only in the GLYPH; registers and GitHub hold public halves. The Owner runs `OPX init`;
anyone else `cgs <ROLE> generate-glyph [--from PATH | --plan]`. It keeps the keys that still match a
grant, makes the rest, seals them (old file kept as `.bak`). For the Owner it replaces register keys and
deploy keys, deleting old ones last, so a failed run is repeated as is. Others get
`~/glyph-request-<uid>.json` to send to the Owner (`OPX admit` replaces the key). A repository gone from
GitHub gets no key and its grant is revoked. A GLYPH this login cannot open is never overwritten. Sizes:
§ 6.

### Registration (`request --register`)

The level asked applies to each repository of the project, except `atCGS` and `omniscience`, always
USR. The file (`examples/registration.toml`) holds the uid, the public key, a proof of possession and one
ssh public key per repository and role; it must not be edited. The uid is told by phone: the file proves
it is consistent, the voice that it is the sender's. `request OUT REPO ROLE …` writes the older JSON form
read by `enrol`/`admit`.

### `intake` and `onboard`

`intake` (no password) checks each file in `~/.cgs/registration/` (format, uid = hash of key, proof,
keys matching the ask) and writes `~/.cgs/intake/<date>.toml`, one `[[person]]` per file with `uid`,
`confirmed = false` and `grant`. Unverifiable files go to `problems`. A project tree that is not the
newest `~/.cgs/<PROJECT>-*/` is named by `[project.<PROJECT>] tree = "…"`.

`onboard --plan` lists persons, levels, what is left, and problems (changed file, missing tree,
uncommitted memory, Owner not admin). The run, for every confirmed person: enrol, publish, pull
`.omniscience` into each project tree, admit, deploy keys (write for OPX/DEV, read-only for USR), commit
and push the project register only. It writes `<date>-<name>.txt` (the message for each newcomer) and
`<date>-report.json`; finished files move to `~/.cgs/registration/done/<date>/`. Every step is safe to
repeat.

By hand, one person: `OPX enrol`, `OPX publish` (workspace); then in the project gate `OPX login
PROJECT pull`, `OPX admit`, `pixi run deploy-keys --repo …` (prints `gh` lines), `OPX login PROJECT
commit` and `push`.

### Newcomer bootstrap

`bootstrap` clones over ssh; without a GitHub key, the `GIT_CONFIG_*` prefix of TUTO 1 D makes git read
over https for that one command; the clones keep their ssh address. A `Run it now? (y/N)` about the
memory branch is answered `y` by the Owner only. `agent_keys: N` is the number of keys loaded; `~/.ssh` is
never used.

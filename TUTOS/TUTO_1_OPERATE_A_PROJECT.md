# TUTO 1 — Operate a new project: who does what

**atCGS 1.9.1-alpha, 2026-11-06.** The running example is the MOLONARI hardware twin,
`MOLO-HRDW`. Parts A and B were run on 2026-11-05. The other parts use the same
commands, but they have **not** been run yet with three new people. Where a step is
untested, it says so.

**The repositories are public: anyone can read them, only keys can write.** So a newcomer
needs no GitHub account and no key to start.

## The people

| Who | What they are | What they do here |
|---|---|---|
| **Owner** | owns the GitHub repositories (today `flipoyo`) and is **atCGS OPX**: the one key pinned in `spec/contracts.toml` | opens projects, enrols people, admits them in a project, installs their keys on GitHub |
| **Project OPX** | a person with the `OPX` role in one project | runs the project: commit, push, tag, release, promote. **Cannot admit anyone.** |
| **DEV** | a person with the `DEV` role in one project | changes code: commit, push, branch, merge |
| **USR** | a person with the `USR` role in one project | reads: status, fetch, pull |

There is only **one** atCGS OPX. A project OPX is just a role in one project, like DEV or USR.
Rights are per project: a DEV on MOLO-HRDW has no right on MOLO-DATA.

## The whole thing in one table

| Step | Who | Does | Command |
|---|---|---|---|
| A | Owner | becomes atCGS OPX (once, already done) | `OPX init` |
| B1 | Owner | declares the project | writes `examples/<project>.cgs` |
| B2 | Owner | installs the project and opens its gate | `cgitsync bootstrap`, `pixi install` |
| B3 | Owner | gives themself rights in the project | `OPX request`, `OPX admit`, `deploy-keys` |
| C1 | Newcomer | gets atCGS (public, no key) | `git clone`, `pixi install` |
| C2 | Newcomer | chooses a login and password, asks for keys | `<ROLE> request` |
| C3 | Owner | enrols the newcomer and publishes | `OPX enrol`, `OPX publish` |
| C4 | Owner | admits the newcomer in the project | `OPX admit` |
| C5 | Owner | installs the newcomer's keys on GitHub | `deploy-keys`, then `gh api …` |
| C6 | Owner | pushes the project's register | `commit --all`, `push --all` |
| D | Newcomer | installs the project and logs in | `cgitsync bootstrap`, `<ROLE> login` |
| E | Everyone | works, each at their level | `<ROLE> login <PROJECT> <op>` |
| F | Owner | removes a right or a person | `OPX revoke` |

Every command starts with `pixi run`. `ATCGS_AUTHORIZE=OPX` in front means: "I, the
operator, allow this OPX command on this machine". It is not a password.

---

## Part A — Owner: become atCGS OPX (once)

**Already done on 2026-11-05.** Skip this part unless you start atCGS from zero.

1. Install the Owner's workspace, the tree atCGS is developed in:
   ```bash
   pixi run cgitsync bootstrap examples/cgs-opx.cgs cgs
   cd ~/.cgs/cgs-<timestamp>
   ```
2. Create the OPX key. It prints `idpub`, your public key:
   ```bash
   ATCGS_AUTHORIZE=OPX pixi run cgs OPX init
   ```
3. Copy `idpub` into `spec/contracts.toml`, `[identity] opx_pub = "…"`. Run `OPX init`
   again with the **same** login and password. It prints `"enrolled": true`.
   This workspace now holds the **master register**: the only place where people are enrolled.
4. Ask for your own keys on the workspace's repositories, admit yourself, install the keys:
   ```bash
   pixi run cgs OPX request ~/opx-cgs.json github:flipoyo/atCGS OPX github:flipoyo/omniscience OPX …
   ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/opx-cgs.json
   pixi run deploy-keys          # prints gh commands: read them, run them
   pixi run cgs OPX login ComplexGraphSync fetch
   ```

From now on, "your workspace" means `~/.cgs/cgs-<timestamp>`.

## Part B — Owner: open a new project

### B1. Declare it

A project is one `.cgs` file in atCGS's `examples/`. Copy `examples/molo_hrdw.cgs`: it lists
the project's repositories, plus three fixed mounts:

- `.atcgs`: atCGS itself, read-only. This is the project's **gate**.
- `.cgitsync/.memory`: the project's memory, holding its **register** (who may do what).
- `.omniscience`: the identities you publish, read-only ([TUTO 2](TUTO_2_OMNISCIENCE.md)).

Check it, then commit and push it from your workspace, so every gate gets it:

```bash
pixi run cgitsync validate examples/<project>.cgs        # DECLARED
pixi run cgs OPX login ComplexGraphSync commit --all "examples: <project>.cgs"
pixi run cgs OPX login ComplexGraphSync push --all
```

Do not declare an `environment` in it: each repository keeps its own `pixi.toml`.

### B2. Install it and open the gate

```bash
pixi run cgitsync bootstrap examples/molo_hrdw.cgs MOLO-HRDW
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi install
```

- If it asks `Run it now? (y/N)` about the memory branch, answer **`y`**. It creates the
  project's own memory branch. Only the Owner does this.
- This is the only step that uses your personal GitHub access. Everything after it goes
  through the gate.

### B3. Give yourself rights in the project

A new project's register is empty. Even you have no right in it yet.

```bash
pixi run cgs OPX request ~/opx-hrdw.json \
  github:flipoyo/MOLONARI-hardware OPX  github:flipoyo/.memory OPX \
  github:flipoyo/atCGS OPX              github:flipoyo/omniscience OPX
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/opx-hrdw.json
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware    # read, then run the gh lines
pixi run cgs OPX login MOLO-HRDW fetch                          # fetched=4  "agent_keys": 4
```

Your GLYPH (the file holding your private keys) has room for 17 keys. If you already hold a
key for a repository (atCGS, omniscience, .memory from Part A), you can reuse it: copy your
earlier request file and keep only those keys in its `keys` list, then `admit` that file.

---

## Part C — Register a new person

Example: Alice will be the project OPX, Bruno a DEV, Chloé a USR, all on MOLO-HRDW.

### C1. Newcomer: get atCGS

You need [Pixi](https://pixi.sh) and git. No GitHub account, no key: atCGS is public.

```bash
git clone --branch CGS-ALPHA https://github.com/flipoyo/atCGS.git ~/atCGS
cd ~/atCGS
pixi install
pixi run cgs --help           # prints the usage: you are ready
```

### C2. Newcomer: choose a login and password, then ask for keys

**Choose them once and write them in your password manager.** atCGS has no account and no
"forgot password". The same pair always gives the same identity; a different pair is a
different person.

- **Login:** any text, e.g. `ada.lovelace`. Not secret. Case and spaces count.
- **Password:** a long passphrase (4 unrelated words, or about 20 characters). This is the
  secret. Nobody can recover it. If you lose it, you start again as a new person.
- Nothing shows while you type. `request` asks the password twice; later commands ask once,
  and a typo there gives you **another** identity (`this UID holds no … grant`).

Ask for one key per repository of the project, with the role the Owner agreed with you:

| Repository | Project OPX | DEV | USR |
|---|---|---|---|
| `github:flipoyo/MOLONARI-hardware` | OPX | DEV | USR |
| `github:flipoyo/.memory` | OPX | DEV | USR |
| `github:flipoyo/atCGS` | USR | USR | USR |
| `github:flipoyo/omniscience` | USR | USR | USR |

Ask for all four, even as USR: a session reaches only the repositories it has a key for.
atCGS and omniscience are USR for everyone but the Owner.

```bash
cd ~/atCGS
pixi run cgs DEV request ~/bruno-hrdw.json \
  github:flipoyo/MOLONARI-hardware DEV  github:flipoyo/.memory DEV \
  github:flipoyo/atCGS USR              github:flipoyo/omniscience USR
```

It prints your `uid`. **Write it down.** Your private keys stay in `~/.cgs/.glyph/`, never
send them. Send the request file (`~/bruno-hrdw.json`) to the Owner by any channel: it holds
only public keys. Tell the Owner your `uid` by a second channel, a call for instance, so
they know the file is yours.

`request` needs the output file **and** at least one `REPOSITORY ROLE` pair. The word after
`cgs` (`DEV` here) only labels the prompts.

### C3. Owner: enrol and publish

In **your workspace** (the master register):

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX enrol ~/requests/bruno-hrdw.json   # check the uid
ATCGS_AUTHORIZE=OPX pixi run cgs OPX publish
```

`enrol` makes the person known to atCGS and grants **nothing**. `publish` puts the new
identity in omniscience, where every project reads it ([TUTO 2](TUTO_2_OMNISCIENCE.md)).

### C4. Owner: admit in the project

From **the project's gate**, in your copy of the project:

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs OPX login MOLO-HRDW pull                         # gets what you just published
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/requests/bruno-hrdw.json
```

It prints the four grants, written in this project's register only.

### C5. Owner: install the keys on GitHub

```bash
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware --repo github:flipoyo/.memory \
  --repo github:flipoyo/atCGS --repo github:flipoyo/omniscience
```

It **prints** one `gh api …/keys` line per grant and runs nothing. Keep the newcomer's lines
(title `atCGS <ROLE> <first 12 characters of the uid>`), read them, run them.

- Only an **admin** of the GitHub repository can run them: on `flipoyo/*`, the Owner only.
  Running them, or not, is how the Owner accepts or refuses someone.
- OPX and DEV keys can push. USR keys are read-only: GitHub refuses their push.

### C6. Owner: push the register

The grants are only in your copy. Push them, so the newcomer's copy will see them:

```bash
pixi run cgs OPX login MOLO-HRDW commit --all "admit Bruno as DEV on MOLO-HRDW"
pixi run cgs OPX login MOLO-HRDW push --all
```

Write commit messages on one line, without `'`.

## Part D — Newcomer: install the project and log in

**After C6.** `bootstrap` clones over ssh (`git@github.com:`) and you have no GitHub key, so
for this one command git reads the public repositories over https. The clones keep their
ssh address: your atCGS keys use it from then on.

```bash
cd ~/atCGS
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf \
GIT_CONFIG_VALUE_0=git@github.com: \
  pixi run cgitsync bootstrap examples/molo_hrdw.cgs MOLO-HRDW
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi install
pixi run cgs DEV login MOLO-HRDW fetch      # Alice: OPX login …   Chloé: USR login …
```

```text
fetched=4 skipped=0
{ "layer": "DEV", "code": "1000", "uid": "…", "twin": "MOLO-HRDW", "agent_keys": 4, "closed": true }
```

- If it asks `Run it now? (y/N)`, answer **`n`**: the memory branch is the Owner's job.
- The word after `cgs` now matters: it is the level you work at, and you must hold it.
- `agent_keys: 4` means your four keys and only them. Your `~/.ssh` is never used.

*Untested: no USR has logged in on a real project yet.*

## Part E — Work

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs DEV login MOLO-HRDW pull
# … edit files in ~/.cgs/MOLO-HRDW-<timestamp>/ …
pixi run cgs DEV login MOLO-HRDW commit "one line, no apostrophe"
pixi run cgs DEV login MOLO-HRDW push
```

`push` sends your commit, and also the project's new state to its memory branch. That is
how the project stays reproducible.

What each level may run through `login`:

| | USR | DEV | Project OPX | Owner (atCGS OPX) |
|---|---|---|---|---|
| `status`, `view-tree`, `fetch`, `pull`, `validate` | yes | yes | yes | yes |
| `add`, `rm`, `commit`, `push`, `branch`, `checkout`, `merge`, `autofix` | no | yes | yes | yes |
| `tag`, `release`, `bootstrap`, `initialise`, `memory`, `promote`, `env`, `verify`, `unlock`, `self-history` | no | no | yes | yes |
| `enrol`, `publish`, `admit`, `revoke` | no | no | **no** | yes |

**Subtwins.** MOLO-TWX contains MOLO-HRDW as `hardware/`: the same repository, the same
branch. What you push in MOLO-HRDW, MOLO-TWX gets with `pull`. But it is another project
with its own register: you need to be admitted there too (C4 to C6 from MOLO-TWX's gate).

## Part F — Owner: remove someone

```bash
# one right in one project: from that project's gate, then C6
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid> github:flipoyo/MOLONARI-hardware
# the person, everywhere: from your workspace, then OPX publish
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid>
```

Then delete their deploy keys on GitHub (`gh api repos/flipoyo/<repo>/keys`, then
`gh api -X DELETE repos/flipoyo/<repo>/keys/<id>`). Revoking in atCGS does not touch GitHub.

---

## If something goes wrong

| You see | Who | Why | Do |
|---|---|---|---|
| `Permission denied (publickey)` at `bootstrap` | newcomer | git used ssh, and you have no key | Part D: the https line in front |
| `DEV request needs OUT then at least one REPOSITORY ROLE pair` | newcomer | `request` without the pairs | C2 |
| `the two passwords differ` | newcomer | a typo in the confirmation | run `request` again |
| `does not match the pinned OPX key` / `is not OPX's pinned key` | anyone but the Owner | only the Owner enrols and admits | send the request file to the Owner |
| `… is done in the master register` | Owner | `enrol`, `publish` or `revoke <uid>` run from a project's gate | run it in your workspace |
| `enrolling a new identity is done in the master register` at `admit` | Owner | the project has not read the new identity yet | `OPX login <PROJECT> pull`, then `admit` again |
| `this UID holds no DEV grant` (or OPX, USR) | newcomer | wrong level, a login or password typo, or C6 not done before D | check the level, retype, ask the Owner for C6 |
| `no key is granted for this repository in this session` | anyone | a repository of the project is missing from the request | `request` it; the Owner admits and installs it |
| `Permission denied (publickey)` at `login` | anyone | the deploy key is not on GitHub | C5 |
| `DEV may not run 'tag' through login` | anyone | not allowed at your level | the table in Part E |
| `branch misalignment … .memory` | Owner | the memory is still on `main` | `OPX login <PROJECT> checkout CGS-MOLO` |
| `failed to parse shell script … single quote` | anyone | a `'` in a commit message | write it without `'` |

Internals (sessions, journals, GLYPH, what is not built) are in
[REFERENCE](operator/REFERENCE.md).

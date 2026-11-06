# TUTO 1 — Operate a new project: who does what

**atCGS 1.12.0-alpha, 2026-11-06.** The running example is the MOLONARI hardware twin,
`MOLO-HRDW`. Parts A and B were run on 2026-11-05. `request --register`, `OPX intake` and
`OPX onboard` (Part C) are covered by tests with local repositories and a fake `gh`; they
have **not** been run yet on the real repositories with real newcomers. Where a step is
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
| C2 | Newcomer | chooses a login and password, writes the registration file | `<ROLE> request --register` |
| C3 | Newcomer | sends the file, unchanged, and gives the uid by phone | e-mail, a call |
| C4 | Owner | saves the files, builds the day's list, confirms each uid | `OPX intake`, edit `confirmed = true` |
| C5 | Owner | **one run**: enrol, publish, admit, deploy keys, push the register | `OPX onboard LIST` |
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
2. **Create your key.** Run `OPX init` for the first time. It asks your OPX login and password
   twice (see C2 for how to choose them), and prints your public key:
   ```bash
   cd ~/.cgs/cgs-<timestamp>
   ATCGS_AUTHORIZE=OPX pixi run cgs OPX init
   ```
   ```json
   { "layer": "OPX", "uid": "35c65c66…d104", "idpub": "qL1FhYN4yQrRd6/cOa92zPG6rsu2t8JXirlntzsYDMo=",
     "pinned": false,
     "next": "copy idpub into spec/contracts.toml [identity] opx_pub, then run OPX init again" }
   ```
   `idpub` is your **public** key: safe to show and to commit. Nothing is written yet.
3. **Pin it, then confirm.** "Pinning" means writing your public key in the one place every atCGS
   reads to know who the Owner is. Every gate and every project trusts a register line only if it
   is signed by that key.
   - Open `spec/contracts.toml` in this workspace (`~/.cgs/cgs-<timestamp>/spec/contracts.toml`)
     and put your `idpub` between the quotes of `opx_pub`:
     ```toml
     [identity]
     opx_pub = "qL1FhYN4yQrRd6/cOa92zPG6rsu2t8JXirlntzsYDMo="
     ```
   - Commit and push that file (it is the repository atCGS, branch `CGS-ALPHA`): projects install
     atCGS from there, so they learn your key from it.
   - Run `OPX init` a **second time**, with exactly the same login and password:
     ```bash
     ATCGS_AUTHORIZE=OPX pixi run cgs OPX init
     # { "layer": "OPX", "uid": "35c65c66…d104", "pinned": true, "enrolled": true }
     ```
     `"pinned": true` says the key you typed is the one written in the file; `"enrolled": true`
     says you are now the first line of the register. A different login or password gives
     `does not match the pinned OPX key`: retype the pair of step 2.

   From now on this workspace holds the **master register**,
   `.cgitsync/.memory/.register/identity.jsonl`: the one list of everybody atCGS knows, and the only
   place where people are enrolled. A project has its own register but only copies this list.
4. Ask for your own keys on the workspace's repositories, admit yourself, install the keys:
   ```bash
   pixi run cgs OPX request ~/opx-cgs.json \
     github:flipoyo/atCGS OPX          github:flipoyo/ComplexGitSync OPX \
     github:flipoyo/omniscience OPX    github:flipoyo/.memory OPX \
     github:flipoyo/.ticketing OPX     github:flipoyo/DevSpec OPX \
     github:flipoyo/DocSpec OPX        github:flipoyo/.dev OPX \
     github:flipoyo/.localSpec OPX     github:flipoyo/.claude OPX
   ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/opx-cgs.json
   pixi run deploy-keys          # prints gh commands: read them, run them
   pixi run cgs OPX login ComplexGraphSync fetch
   ```

These ten are the repositories of `examples/cgs-opx.cgs`, the tree you installed in step 1: list
them with `grep -o 'repository = "[^"]*"' examples/cgs-opx.cgs`, and give each the role `OPX`.

**Before creating a new user, verify your credentials.** Your rights are written in several
registers (the master register of the workspace, and one per project tree) and your private keys
are in your GLYPH, `~/.cgs/.glyph/<uid>.glyph`. A login works only where a grant **and** its key in
the GLYPH meet. One command, from any directory, shows all of it:

```bash
pixi run cgs OPX user-credential
```

It asks your login and password once, writes nothing, and prints:

```text
uid      35c65c66…d104   (atCGS OPX: the pinned key)
glyph    10 key(s), 4310 of 8159 bytes used

register                  identity    grants  published
master cgs-20261105…      enrolled    10      -
MOLO-HRDW                 enrolled    4       listed

repository                          role  fingerprint             granted in / verdict
flipoyo/atcgs                       OPX   SHA256:HqwTmd…          master, MOLO-HRDW  ok
flipoyo/molonari-hardware           OPX   SHA256:Y31s0f…         MOLO-HRDW  ok
```

One row per repository and role, with a verdict:

| Verdict | Means | Do |
|---|---|---|
| `ok` | granted, and its key is in your GLYPH | nothing |
| `no key` | granted, but the key is not in your GLYPH (or there is no GLYPH: `glyph MISSING`) | no login can work for it. Recover the GLYPH, or `request` new keys, `admit` them and install the deploy keys again (C5) |
| `not admitted` | the key is in your GLYPH, granted nowhere (an orphan, it takes room for nothing) | `admit` it, or ignore it |
| `revoked` | the identity was revoked | ask the Owner |
| `refused by GitHub` | with `--probe`: the deploy key is not (or no longer) on GitHub | install it (C5) |

Options: `--probe` tries each key on GitHub (one `git ls-remote` per key, through the session, never
`~/.ssh`); `--json` prints the same as data; `--tree PATH` reads only that tree. The exit status is
0 when every grant is `ok`, 1 otherwise. Any user runs it with their own level
(`DEV user-credential`); the word only labels the prompts.

**`OPX onboard` runs this check on you first** and stops if the GLYPH is missing or a grant of the
memory or omniscience repositories has no key. Run it yourself before you start.

**Your GLYPH is lost (`glyph MISSING`, every row `no key`).** A GLYPH cannot be rebuilt from the
repositories: your private keys were only ever in that file. The registers and GitHub hold public
halves, which open nothing. Two ways out:

```bash
# 1. you still have a copy (a backup, a USB key, another machine): take it back
pixi run cgs OPX generate-glyph --from /path/to/copy-or-folder
# 2. you do not: make new keys, for exactly the access you already have
pixi run cgs OPX generate-glyph --plan      # shows what it would do, writes nothing
pixi run cgs OPX generate-glyph
```

The second asks your login and password once, prints the plan, and on `y`:

1. keeps any key your GLYPH still holds that matches a grant, and makes a new one for each other
   (repository, role) you hold a grant for, in any register of `~/.cgs`;
2. seals them in a new GLYPH (an older one is kept next to it as `.bak`);
3. **atCGS OPX only:** replaces the key in each register that carries the old one (a revoke and a
   grant, signed by you), installs the new deploy key on GitHub, commits and pushes each register, and
   only then deletes the old deploy keys from GitHub, so nothing is lost if a step fails: run the same
   command again, it picks up where it stopped;
4. **anyone else:** writes `~/glyph-request-<uid>.json`, public keys only. Send it to the Owner, who runs
   `OPX admit` on it from the project's gate (it replaces the key of a grant you already have), installs
   the deploy keys (C5) and pushes the register.

A repository that is no longer on GitHub gets no key; its grant is revoked in the registers. A GLYPH
that this login and password cannot open is never overwritten.

Run `user-credential` again: every row should read `ok`.

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

### C2. Newcomer: choose a login and password, then write the registration file

**Choose them once and write them in your password manager.** atCGS has no account and no
"forgot password". The same pair always gives the same identity; a different pair is a
different person.

- **Login:** any text, e.g. `ada.lovelace`. Not secret. Case and spaces count.
- **Password:** a long passphrase (4 unrelated words, or about 20 characters). This is the
  secret. Nobody can recover it. If you lose it, you start again as a new person.
- Nothing shows while you type. The command asks the password twice; later commands ask
  once, and a typo there gives you **another** identity (`this UID holds no … grant`).

Say which project you work on and at which level. atCGS knows the repositories and the
keys to ask for, so you type no repository:

```bash
cd ~/atCGS
pixi run cgs DEV request --register MOLO-HRDW=DEV --name "Bruno" ~/bruno.toml
# several projects: --register MOLO-HRDW=DEV --register MOLO-TWX=USR
```

It prints your `uid` (**write it down**) and writes `~/bruno.toml`. Your private keys stay
sealed in `~/.cgs/.glyph/`, never send them. The word after `cgs` only labels the prompts;
the level you ask is the one after `=`.

For each repository of the project, the level is the one you asked, except `atCGS` and
`omniscience`, which are always USR: the gate and the published identities are written by
the Owner only.

The file is this one, with your own values (`examples/registration.toml`):

```toml
# atCGS registration. Send this file, unchanged, to the Owner.
# It holds only public data: your uid, your public key, the public halves of your ssh keys.
# Tell the Owner your uid by another channel (a call): it is how they know this file is yours.
format  = "atcgs-registration/1"         # the format version; do not change
name    = "Ada"                          # your name, for the Owner's report only; never written to a register
uid     = "0000000000000000000000000000000000000000000000000000000000000000"   # sha256 of your public key
created = 2026-11-06T10:42:00Z

[ask]                                    # what you ask for, per project; the Owner decides
MOLO-HRDW = "DEV"

[request]                                # what the Owner's `admit` needs
pub   = "…base64…"                       # your public key
proof = "…base64…"                       # proof that you hold the private key
keys  = [                                # one ssh public key per repository and role; the private halves stay in your GLYPH
  { repo = "github:flipoyo/MOLONARI-hardware", role = "DEV", ssh = "ssh-ed25519 AAAA…" },
  { repo = "github:flipoyo/.memory", role = "DEV", ssh = "ssh-ed25519 AAAA…" },
  { repo = "github:flipoyo/atCGS", role = "USR", ssh = "ssh-ed25519 AAAA…" },
  { repo = "github:flipoyo/omniscience", role = "USR", ssh = "ssh-ed25519 AAAA…" },
]
```

It holds only public data. Do not edit it: the Owner's tool checks it.

### C3. Newcomer: send the file, and your uid by another channel

Send `~/bruno.toml`, unchanged, to the Owner (e-mail, a chat, a USB key). Then **tell the Owner
your uid by phone or in person.** The uid in the file only proves the file is consistent;
your voice proves it is yours.

### C4. Owner: save the files, build the list, confirm each uid

Save each received file in `~/.cgs/registration/`. No renaming, no editing.

```bash
pixi run cgs OPX intake
# { "list": "~/.cgs/intake/2026-11-06.toml", "persons": 3, "confirmed": 0, "problems": [] }
```

`intake` needs no password. It verifies every file (format, the uid is the hash of the key,
the proof of possession, the keys match what was asked) and writes the day's list. A file it
cannot verify is named in `problems` and left out. Open the list:

```toml
[[person]]
name         = "Bruno"
registration = "~/.cgs/registration/bruno.toml"
sha256       = "…"          # of the file as intake read it
uid          = "e9b6c66e…"  # read it to Bruno on the phone
confirmed    = false        # → true once he confirmed it
grant        = { MOLO-HRDW = "DEV" }   # what he asked; you may change a level
```

Set `confirmed = true` for each person whose uid you checked. That is your only manual edit.
If the project tree is not the newest `~/.cgs/<PROJECT>-*/`, add
`[project.MOLO-HRDW]` with `tree = "…"` at the end of the list.

### C5. Owner: one run

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX onboard ~/.cgs/intake/2026-11-06.toml --plan   # read, check, print: writes nothing
ATCGS_AUTHORIZE=OPX pixi run cgs OPX onboard ~/.cgs/intake/2026-11-06.toml
```

The first command prints a table (person, project, level, what is still to do) and every
problem it found: a changed file, a missing tree, uncommitted changes in the project's
memory, you not being admin of a repository. Fix them and run it again.

The second asks **your OPX login and password once**, then `Apply this plan? (y/N)`. On `y` it,
for everyone confirmed: enrols them (master register), publishes the identities, pulls
`.omniscience` into each project tree, admits them there, installs their keys on GitHub as
deploy keys (write for OPX and DEV, read-only for USR, skipping those already there), and
commits and pushes the project's register alone (never `--all`).

It then writes, in `~/.cgs/intake/`: `2026-11-06-<name>.txt`, the message to send to each
newcomer (Part D with their own project and level), and `2026-11-06-report.json`, one line
per step. Registration files whose steps all went well move to
`~/.cgs/registration/done/2026-11-06/`. A step that failed stays in the report and its file
stays in the folder: fix the cause and run the same command again, every step is safe to repeat.

Send each newcomer their message. Go to Part D.

*Untested on the real repositories.*

<details>
<summary>By hand, what the run does (one person, one project)</summary>

```bash
# in your workspace
ATCGS_AUTHORIZE=OPX pixi run cgs OPX enrol ~/.cgs/registration/bruno.json   # a request in the old JSON form
ATCGS_AUTHORIZE=OPX pixi run cgs OPX publish
# in the project's gate
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs OPX login MOLO-HRDW pull
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/.cgs/registration/bruno.json
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware --repo github:flipoyo/.memory \
  --repo github:flipoyo/atCGS --repo github:flipoyo/omniscience     # prints gh lines: read, run
pixi run cgs OPX login MOLO-HRDW commit --all "admit Bruno as DEV on MOLO-HRDW"
pixi run cgs OPX login MOLO-HRDW push --all
```

`request OUT REPO ROLE …` still writes the JSON form these commands read.
</details>

## Part D — Newcomer: install the project and log in

**After C5.** `bootstrap` clones over ssh (`git@github.com:`) and you have no GitHub key, so
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

After your first `login`, `pixi run cgs <ROLE> user-credential` shows what the project knows of you.

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
with its own register: you need to be admitted there too (list it under MOLO-TWX in the same `OPX onboard`).

## Part F — Owner: remove someone

```bash
# one right in one project: from that project's gate, then commit and push as in the annex of C5
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
| `DEV request needs OUT then at least one REPOSITORY ROLE pair` | newcomer | `request` without the pairs | use `request --register PROJECT=ROLE OUT.toml` (C2) |
| `the plan has N problem(s), nothing was done` | Owner | `onboard` found something wrong | read the list it printed, fix, run again (C5) |
| `no person is confirmed` | Owner | every `confirmed` is still `false` | check the uids, set `confirmed = true` (C4) |
| `the registration file changed since intake` | Owner | a file was edited or replaced after `intake` | `OPX intake`, confirm again |
| `the two passwords differ` | newcomer | a typo in the confirmation | run `request` again |
| `does not match the pinned OPX key` / `is not OPX's pinned key` | anyone but the Owner | only the Owner enrols and admits | send the request file to the Owner |
| `… is done in the master register` | Owner | `enrol`, `publish` or `revoke <uid>` run from a project's gate | run it in your workspace |
| `enrolling a new identity is done in the master register` at `admit` | Owner | the project has not read the new identity yet | `OPX login <PROJECT> pull`, then `admit` again |
| `this UID holds no DEV grant` (or OPX, USR) | newcomer | wrong level, a login or password typo, or C5 not done before D | check the level, retype, ask the Owner for C5 |
| `no key is granted for this repository in this session` | anyone | a repository of the project is missing from the request | `request` it; the Owner admits and installs it |
| `no GLYPH for this login/password`, `the GLYPH holds no key` | anyone | the GLYPH is missing or lacks a key | `pixi run cgs <ROLE> user-credential` shows which; see its `no key` row |
| `Permission denied (publickey)` at `login` | anyone | the deploy key is not on GitHub | C5: read the report, run `OPX onboard` again |
| `DEV may not run 'tag' through login` | anyone | not allowed at your level | the table in Part E |
| `branch misalignment … .memory` | Owner | the memory is still on `main` | `OPX login <PROJECT> checkout CGS-MOLO` |
| `failed to parse shell script … single quote` | anyone | a `'` in a commit message | write it without `'` |

Internals (sessions, journals, GLYPH, what is not built) are in
[REFERENCE](operator/REFERENCE.md).

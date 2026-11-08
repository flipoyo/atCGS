# TUTO 1 — Operate a new project: who does what

**atCGS 1.13.0-alpha, 2026-11-06.** The running example is the MOLONARI hardware twin,
`MOLO-HRDW`. Parts A and B were run on 2026-11-05. `request --register`, `OPX intake` and
`OPX onboard` (Part C) are covered by tests with local repositories and a fake `gh`; they
have **not** been run yet on the real repositories with real newcomers. Where a step is
untested, it says so.

**The repositories are public: anyone can read them, only keys can write.** So a newcomer
needs no GitHub account and no key to start.

## The people

| Who | What they are | What they do here |
|---|---|---|
| **Owner** | owns the GitHub repositories (today `flipoyo`) and is **atCGS OPX**: the one key pinned in `spec/opx.toml` | opens projects, enrols people, admits them in a project, installs their keys on GitHub |
| **Project OPX** | a person with the `OPX` role in one project | runs the project: commit, push, tag, release, promote. **Cannot admit anyone.** |
| **DEV** | a person with the `DEV` role in one project | changes code: commit, push, branch, merge |
| **USR** | a person with the `USR` role in one project | reads: status, fetch, pull |

There is only **one** atCGS OPX. A project OPX is just a role in one project, like DEV or USR.
Rights are per project: a DEV on MOLO-HRDW has no right on MOLO-DATA.

## The whole thing in one table

| Step | Who | Does | Command |
|---|---|---|---|
| A | Owner | becomes atCGS OPX, on any machine | `OPX init` |
| B1 | Owner | declares the project | writes `examples/<project>.cgs` |
| B2 | Owner | installs the project and opens its gate | `cgitsync bootstrap`, `pixi install` |
| B3 | Owner | becomes OPX of the project | `OPX init PROJECT` |
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

## Part A — Owner: become atCGS OPX, on this machine or another

One command, whatever the state of the machine. It reads the state and does what is missing; run
again, it changes nothing. You edit no file.

```bash
git clone --branch CGS-ALPHA https://github.com/flipoyo/atCGS.git ~/atCGS     # a plain clone is enough
cd ~/atCGS && pixi install
pixi run gh auth login                                  # once per machine: your own GitHub account, the repositories' owner
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init --plan        # shows what it would do, writes nothing
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init
```

`gh` (the GitHub CLI) comes with `pixi install`. atCGS uses it, and only it, to install the deploy keys on
GitHub; that is why the Owner logs it in. If it is missing or logged out, the plan says so under
`problems` and the run stops before asking anything.

It asks your login and password (once; **twice** when the key is new, see C2 for how to choose them),
prints its plan and asks `Apply this plan? (y/N)`. The plan depends on what it finds:

| The machine is | `OPX init` does |
|---|---|
| **a new atCGS, no key pinned** | installs the workspace if it is missing (`cgitsync bootstrap examples/cgs-alpha.cgs`, over https, no key needed); makes your key and **pins** it by appending it to `spec/opx.toml`; enrols you in the master register; makes one ssh key per repository of the workspace and seals them in your GLYPH; grants you OPX on each; installs the deploy keys on GitHub; commits and pushes the pin and the register; publishes the identities |
| **another machine, you are already OPX** | says so, and rebuilds your GLYPH for the access you already hold (`--from PATH` takes a copy you still have; otherwise new keys, registers and GitHub updated, old deploy keys removed last). It never enrols you again |
| **everything is in order** | prints the `user-credential` table below and changes nothing |
| **a key is pinned, but this is another login** | refuses: there is one OPX |

*Pinning* means writing your public key where every atCGS reads who the Owner is: a register line
is trusted only if it is signed by that key. `init` writes it, in `spec/opx.toml`, by appending a block, never
rewriting the file (earlier pins stay as history), and pushes it so every gate learns it. The master
register it fills, `.cgitsync/.memory/.register/identity.jsonl`, is the one list of everybody atCGS knows
and the only place where people are enrolled; a project's register only copies it.

There is one branch for the whole alpha series, `CGS-ALPHA`. `init` refuses to run from an atCGS that is
behind it (`git pull` first). A push of atCGS itself is refused while `pixi run test` fails
(`ATCGS_SKIP_TESTS=1` skips it).

### Verify your credentials: `user-credential`

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
| `no key` | granted, but the key is not in your GLYPH (or there is no GLYPH: `glyph MISSING`) | no login can work for it: `OPX init` rebuilds the GLYPH |
| `not admitted` | the key is in your GLYPH, granted nowhere (an orphan, it takes room for nothing) | `admit` it, or ignore it |
| `revoked` | the identity was revoked | ask the Owner |
| `refused by GitHub` | with `--probe`: the deploy key is not (or no longer) on GitHub | `OPX init` installs it again |

Options: `--probe` tries each key on GitHub (one `git ls-remote` per key, through the session, never
`~/.ssh`); `--json` prints the same as data; `--tree PATH` reads only that tree. The exit status is
0 when every grant is `ok`, 1 otherwise. Any user runs it with their own level
(`DEV user-credential`); the word only labels the prompts. **`OPX onboard` runs this check on you
first** and stops if the GLYPH is missing or a grant of the memory or omniscience repositories has no key.

### If your GLYPH is lost

A GLYPH cannot be rebuilt from the repositories: your private keys were only ever in that file. The
registers and GitHub hold public halves, which open nothing. On the Owner's machine `OPX init` (above)
makes new keys for exactly the access you hold; anyone else uses `generate-glyph`:

```bash
pixi run cgs <ROLE> generate-glyph --from /path/to/copy-or-folder     # you still have a copy: take it back
pixi run cgs <ROLE> generate-glyph --plan                             # you do not: what it would do
pixi run cgs <ROLE> generate-glyph
```

It keeps any key your GLYPH still holds that matches a grant, makes new ones for the rest, seals them (an
older GLYPH is kept as `.bak`), and, for the Owner, replaces the key in each register, installs the new
deploy key on GitHub, pushes the registers, and only then deletes the old deploy keys, so nothing is lost
if a step fails: run the same command again. Anyone else gets `~/glyph-request-<uid>.json` (public keys
only) to send to the Owner, whose `OPX admit` replaces the key of a grant already held. A repository that
is no longer on GitHub gets no key and its grant is revoked. A GLYPH that this login cannot open is never
overwritten.

**The GLYPH grows by itself.** It starts at 8 KiB (about 17 keys); when the keys no longer fit it becomes
32 KiB (about 69), then 128 KiB, and so on, always by a factor 4. It never shrinks, and its size never tells
how many keys it holds. A GLYPH of the older, smaller size opens unchanged.

## Part B — Owner: open a new project

Part A first: B3 reuses the GLYPH that A made, and refuses to start without it.

### B1. Declare it (a new project only)

**MOLO-HRDW is already declared** (`examples/molo_hrdw.cgs`, like the other MOLONARI twins): skip B1
and go to B2. B1 is for a project atCGS does not know yet: it writes the file that every later step
reads by the project's name.

A project is one `.cgs` file in atCGS's `examples/`. Copy `examples/molo_hrdw.cgs`: it lists
the project's repositories, plus three fixed mounts:

- `.atcgs`: atCGS itself, read-only. This is the project's **gate**.
- `.cgitsync/.memory`: the project's memory, holding its **register** (who may do what).
- `.omniscience`: the identities you publish, read-only ([TUTO 2](TUTO_2_OMNISCIENCE.md)).

Check it, then commit and push it from your workspace (the tree `OPX init` installed), so every gate gets it:

```bash
cd ~/.cgs/cgs-<timestamp>
pixi run cgitsync validate examples/<project>.cgs        # DECLARED
pixi run cgs OPX login cgs commit --all "examples: <project>.cgs"
pixi run cgs OPX login cgs push --all
```

Do not declare an `environment` in it: each repository keeps its own `pixi.toml`.

### B2. Install it and open the gate (optional: B3 does it)

B3 installs the project's tree itself, over https, when there is none. Do B2 by hand only to choose
when the tree is installed.

```bash
pixi run cgitsync bootstrap examples/molo_hrdw.cgs MOLO-HRDW
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi install
```

- If it asks `Run it now? (y/N)` about the memory branch, answer **`y`**. It creates the
  project's own memory branch. Only the Owner does this.
- Your personal GitHub access is used here and by `gh` (deploy keys). Everything else goes
  through the gate.

### B3. Make yourself OPX of the project

A new project's register is empty: even you have no right in it yet. Run it after Part A succeeded
(`user-credential` shows `glyph … key(s)`, not `glyph MISSING`).

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init MOLO-HRDW --plan       # what it would do
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init MOLO-HRDW
```

It finds the project's tree (or installs it, as in B2), grants you OPX on every repository of its `.cgs`,
**reusing the keys your GLYPH already holds** for the same repository and role (atCGS, omniscience and
`.memory` are shared with the workspace, so MOLO-HRDW costs one new key, for MOLONARI-hardware), installs the
deploy keys that are new, and pushes the project's register. One password, one `y`.

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
| `OPX requires explicit owner authorization` | Owner | `ATCGS_AUTHORIZE=OPX` missing, `--plan` included | type it in front of the command |
| `gh (GitHub CLI) is not on PATH` in `problems` | Owner | `pixi install` not run since `gh` joined `pixi.toml` (2026-11-08) | `pixi install` (A) |
| `gh is not logged in to GitHub` in `problems` | Owner | `gh auth login` not done on this machine | `pixi run gh auth login` (A) |
| `no GLYPH for this login on this machine` at `OPX init PROJECT` | Owner | B3 before A | `ATCGS_AUTHORIZE=OPX pixi run cgs OPX init` (A), then B3 |
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

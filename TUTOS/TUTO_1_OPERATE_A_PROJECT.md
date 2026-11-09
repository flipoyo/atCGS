# TUTO 1 — Operate a new project: who does what

**atCGS 1.13.2-alpha, 2026-11-09.** Example: the MOLONARI hardware twin, `MOLO-HRDW`. Parts A and B
ran on 2026-11-05; Part C is covered by tests only. Explanations are in
[REFERENCE § 11](operator/REFERENCE.md#11-operating-a-project-the-details-behind-tuto-1).

The repositories are public: a newcomer needs no GitHub account and no key to start.

## The people

| Who | Does |
|---|---|
| **Owner** (atCGS OPX, one key pinned in `spec/opx.toml`) | opens projects, admits people, installs their keys |
| **Project OPX** | runs one project: commit, push, tag, release. Admits nobody |
| **DEV** | changes code in one project |
| **USR** | reads one project |

Rights are per project. Every command starts with `pixi run`; `ATCGS_AUTHORIZE=OPX` in front allows an
OPX command on this machine (it is not a password).

## Steps

| Step | Who | Command |
|---|---|---|
| A | Owner | `OPX init` |
| B1 | Owner | write and validate `examples/<project>.cgs` (new project only) |
| B2 | Owner | `OPX init PROJECT` |
| C1 | Newcomer | `git clone`, `pixi install` |
| C2 | Newcomer | `<ROLE> request --register` |
| C3 | Newcomer | send the file, say the uid by phone |
| C4 | Owner | `OPX intake`, set `confirmed = true` |
| C5 | Owner | `OPX onboard LIST` |
| D | Newcomer | `cgitsync bootstrap`, `<ROLE> login` |
| E | Everyone | `<ROLE> login <PROJECT> <op>` |
| F | Owner | `OPX revoke` |

---

## A — Owner: become atCGS OPX (any machine, run again = no change)

```bash
git clone --branch CGS-ALPHA https://github.com/flipoyo/atCGS.git ~/atCGS
cd ~/atCGS && pixi install
pixi run gh auth login                                  # once per machine, the repositories' owner account
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init --plan        # writes nothing
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init               # login, password, then y
pixi run cgs OPX user-credential                        # every row must read ok
```

Choose the login and password as in C2. Lost GLYPH, verdicts other than `ok`: REFERENCE § 11.

## B — Owner: open a project

### B1. Declare it (a new project only)

MOLO-HRDW is already declared (`examples/molo_hrdw.cgs`): skip to B2.

For a new project, copy `examples/molo_hrdw.cgs` to `examples/<project>.cgs` in `~/atCGS`, list its
repositories, keep the three fixed mounts (`.atcgs` the gate, `.cgitsync/.memory` the register,
`.omniscience` the published identities, see [TUTO 2](TUTO_2_OMNISCIENCE.md)), and declare no
`environment`. Then:

```bash
cd ~/atCGS
pixi run cgitsync validate examples/<project>.cgs        # DECLARED
```

Nothing is committed here: no project tree exists yet. B2 reads the file from `~/atCGS`.

### B2. Install it and make yourself its OPX

```bash
cd ~/atCGS
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init MOLO-HRDW --plan
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init MOLO-HRDW      # one password, one y
```

It bootstraps the project tree when there is none, grants you OPX on each repository, reuses your GLYPH
keys, installs the new deploy keys and pushes the project register. Needs Part A first.

## C — Register a newcomer

Example: Bruno, DEV on MOLO-HRDW.

### C1. Newcomer: get atCGS

```bash
git clone --branch CGS-ALPHA https://github.com/flipoyo/atCGS.git ~/atCGS
cd ~/atCGS && pixi install
```

### C2. Newcomer: choose a login and password, write the file

Write both in a password manager. There is no recovery: the same pair is the same identity, another
pair is another person. Login: any text, not secret. Password: a long passphrase.

```bash
cd ~/atCGS
pixi run cgs DEV request --register MOLO-HRDW=DEV --name "Bruno" ~/bruno.toml
```

Write down the printed `uid`. The file holds only public data; do not edit it.

### C3. Newcomer: send it

Send `~/bruno.toml` unchanged to the Owner, then tell the Owner the uid by phone or in person.

### C4. Owner: check

Save the files, unrenamed, in `~/.cgs/registration/`, then:

```bash
pixi run cgs OPX intake        # writes ~/.cgs/intake/<date>.toml
```

In that list, set `confirmed = true` for each uid checked by phone.

### C5. Owner: onboard

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX onboard ~/.cgs/intake/<date>.toml --plan
ATCGS_AUTHORIZE=OPX pixi run cgs OPX onboard ~/.cgs/intake/<date>.toml
```

Fix the problems the plan lists, run again. Then send each newcomer their `~/.cgs/intake/<date>-<name>.txt`.

## D — Newcomer: install and log in

```bash
cd ~/atCGS
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf \
GIT_CONFIG_VALUE_0=git@github.com: \
  pixi run cgitsync bootstrap examples/molo_hrdw.cgs MOLO-HRDW
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi install
pixi run cgs DEV login MOLO-HRDW fetch      # answer n to "Run it now?"
```

## E — Work

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs DEV login MOLO-HRDW pull
pixi run cgs DEV login MOLO-HRDW commit "one line, no apostrophe"
pixi run cgs DEV login MOLO-HRDW push
```

| | USR | DEV | Project OPX | Owner |
|---|---|---|---|---|
| `status`, `view-tree`, `fetch`, `pull`, `validate` | yes | yes | yes | yes |
| `add`, `rm`, `commit`, `push`, `branch`, `checkout`, `merge`, `autofix` | no | yes | yes | yes |
| `tag`, `release`, `bootstrap`, `initialise`, `memory`, `promote`, `env`, `verify`, `unlock`, `self-history` | no | no | yes | yes |
| `enrol`, `publish`, `admit`, `revoke` | no | no | no | yes |

A subtwin (MOLO-TWX holds MOLO-HRDW) is another project with its own register: admit there too.

## F — Owner: remove someone

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid> github:flipoyo/MOLONARI-hardware   # one right, from the project gate
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid>                                     # the person, from the workspace, then OPX publish
```

Then delete their deploy keys on GitHub (`gh api repos/flipoyo/<repo>/keys`, then
`gh api -X DELETE repos/flipoyo/<repo>/keys/<id>`).

---

## If something goes wrong

| You see | Do |
|---|---|
| `OPX requires explicit owner authorization` | put `ATCGS_AUTHORIZE=OPX` in front |
| `gh … is not on PATH` / `gh is not logged in` | `pixi install` / `pixi run gh auth login` (A) |
| `no GLYPH for this login on this machine` at `OPX init PROJECT` | Part A first |
| `Permission denied (publickey)` at `bootstrap` | the https prefix of Part D |
| `Permission denied (publickey)` at `login` | Owner: read the report, run `OPX onboard` again |
| `the plan has N problem(s)` | fix what it printed, run again |
| `no person is confirmed` | set `confirmed = true` (C4) |
| `the registration file changed since intake` | `OPX intake`, confirm again |
| `this UID holds no DEV grant` | check level, password, or that C5 was done |
| `no GLYPH …`, `the GLYPH holds no key` | `pixi run cgs <ROLE> user-credential` |
| `… is done in the master register` | run it from the workspace, not a project gate |
| `enrolling a new identity is done in the master register` at `admit` | `OPX login <PROJECT> pull`, then `admit` |
| `DEV may not run 'tag' through login` | not your level (table E) |
| `branch misalignment … .memory` | `OPX login <PROJECT> checkout CGS-MOLO` |
| `failed to parse shell script … single quote` | no `'` in the commit message |

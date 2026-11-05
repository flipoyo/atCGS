# TUTO 02 — Emulate a twin: install MOLONARI, open its gate, get admitted

**Run on 2026-11-05** (atCGS 1.9.0-alpha) for MOLO-HRDW and MOLO-TWX. The outputs are
the real ones, shortened.

**What you get at the end:** a MOLONARI twin installed on your machine, its gate open,
and your rights on it written in its register. "Emulate" means exactly this: the twin is
rebuilt from its description and its memory, on any machine, identical every time.

**Who acts:** OPX installs the twin and admits users. A user only needs TUTO 01 first.

## 1. Choose the twin

Each MOLONARI twin is one file in `examples/` of atCGS:

| You want to work on | Install | Repositories |
|---|---|---|
| the hardware only | `molo_hrdw.cgs` → **MOLO-HRDW** | MOLONARI-hardware |
| the data only | `molo_data.cgs` → **MOLO-DATA** | MOLONARI-data |
| the computation only | `molo_cmpt.cgs` → **MOLO-CMPT** | MOLONARI-computo |
| everything | `molo_twx.cgs` → **MOLO-TWX** | MOLONARI1D, with the three above as `hardware/`, `data/`, `pyheatmy/` |

Each also mounts the gate (`.atcgs`), the twin's memory (`.cgitsync/.memory`) and the
published identities (`.omniscience`). Open one: a `.cgs` file is short and readable.

## 2. OPX: install it

From an atCGS checkout (the operator's workspace):

```bash
pixi run cgitsync bootstrap examples/molo_hrdw.cgs MOLO-HRDW
```

```text
To use this workspace, run:
  export CGSHOME=/home/you/.cgs/MOLO-HRDW-20261105184338
warning: .memory has no branch 'ComplexGitSync_MOLO-HRDW_CGS-MOLO' yet, so it was cloned on 'main'. …
Run it now? (y/N) [n]: y
branch=ComplexGitSync_MOLO-HRDW_CGS-MOLO set_up=no pushed=yes
… "tree_lifecycle_state": "READY"
```

- **Answer `y`.** It creates the twin's own memory branch. Without it the twin would
  record its states on `main`, shared with everyone.
- This one step runs with your usual ssh access: the gate does not exist until the twin
  is installed. Every later step goes through the gate.
- The twin lands in `~/.cgs/<TWIN>-<timestamp>/`. Repeat for `molo_twx.cgs` with
  `MOLO-TWX` to get the access point.

## 3. OPX: open the gate

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi install
```

The gate is atCGS itself, checked out read-only in the twin. Its first `pixi install`
downloads the pinned ComplexGitSync.

## 4. OPX: admit yourself first

A new twin's register is empty: even OPX has no right on it yet. Ask for keys on the
twin's repositories exactly as a user does (TUTO 01 step 2, with `OPX` instead of `DEV`),
then admit your own request from this twin's gate:

```bash
pixi run cgs OPX request ~/opx-hrdw.json \
  github:flipoyo/MOLONARI-hardware OPX  github:flipoyo/.memory OPX \
  github:flipoyo/atCGS OPX              github:flipoyo/omniscience OPX
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/opx-hrdw.json
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware   # … the repositories that are new for you
pixi run cgs OPX login MOLO-HRDW fetch
# fetched=4 skipped=0   "agent_keys": 4
```

Each key you request takes room in your GLYPH (17 keys at most). An operator who already
holds keys for these repositories, from another twin, can grant those same public keys
instead of new ones: [OPX 05](operator/OPX_05_SECOND_MISSION.md) § 6 shows how. That is
what was done on 2026-11-05.

## 5. OPX: admit the users

For each user who sent a request (TUTO 01), from **this twin's** gate:

```bash
pixi run cgs OPX login MOLO-HRDW pull                       # fetch the latest published identities
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/dev-hrdw.json
```

```json
{ "uid": "e9b6c66e…", "granted": [
    { "repo": "github:flipoyo/MOLONARI-hardware", "role": "DEV", … },
    { "repo": "github:flipoyo/.memory",           "role": "DEV", … },
    { "repo": "github:flipoyo/atCGS",             "role": "USR", … },
    { "repo": "github:flipoyo/omniscience",       "role": "USR", … } ] }
```

`admit` copies the published identities into this twin's register, then writes the
user's grants **in this twin only**. The `pull` first matters: the twin reads the
identities from its own `.omniscience` checkout, and right after a `publish` that
checkout is behind (without it: `enrolling a new identity is done in the master register`).

## 6. OPX: put the keys on GitHub

```bash
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware --repo github:flipoyo/.memory \
  --repo github:flipoyo/atCGS --repo github:flipoyo/omniscience
```

It prints one `gh api …/keys` command per grant on those repositories, and runs nothing.
Keep the user's lines (title `atCGS DEV e9b6c66e4af7`, `atCGS USR e9b6c66e4af7`), read
them, run them. A USR key is installed **read-only** (`read_only=true`): GitHub itself
refuses a push with it.

## 7. You: check your access

Now the user, with **their** login and password:

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs DEV login MOLO-HRDW fetch
```

```text
fetched MOLO-HRDW: origin
fetched atCGS: origin
fetched .memory: origin
fetched omniscience: origin
fetched=4 skipped=0
{ "layer": "DEV", "code": "1000", "uid": "e9b6c66e…", "twin": "MOLO-HRDW", "agent_keys": 4, "cgitsync": 0, "closed": true }
```

`agent_keys: 4` is your four keys, and only them: never the operator's, never `~/.ssh`.
The session's ssh-agent is gone when the command ends (`"closed": true`).

## Done

The twin is emulated and you are admitted on it. Next: [TUTO 03](TUTO_03_SUBTWINS.md),
your first change.

## If something goes wrong

| You see | Why | Do |
|---|---|---|
| `enrolling a new identity is done in the master register` at `admit` | the twin has not seen the published identity yet | `… OPX login <TWIN> pull`, then `admit` again |
| `this UID holds no DEV grant` | not admitted on this twin (rights are per twin) | ask OPX to `admit` you here |
| `no key is granted for this repository in this session` | a repository of the twin is missing from your request | `request` it, OPX `admit`s and installs the key |
| `Permission denied (publickey)` | the deploy key is not on GitHub yet | step 6 |
| `branch misalignment … .memory` | the memory is still on `main` | `… OPX login <TWIN> checkout CGS-MOLO` |

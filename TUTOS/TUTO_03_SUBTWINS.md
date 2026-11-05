# TUTO 03 — Work through subtwins: change MOLO-HRDW, see it in MOLO-TWX

**Run on 2026-11-05** (atCGS 1.9.0-alpha): a DEV committed and pushed on MOLO-HRDW, and
MOLO-TWX showed the same commit. The outputs are the real ones, shortened.

**What you get at the end:** your first change on a MOLONARI twin, pushed through the
gate, recorded in the twin's memory, and visible in every twin that contains it.

**Who acts:** you, a DEV admitted on MOLO-HRDW (TUTO 02).

## 1. The idea: a twin made of twins

MOLO-TWX is MOLONARI1D with the three subtwins inside it:

```text
MOLO-TWX/              MOLONARI1D          ← the access point
├── hardware/          MOLONARI-hardware   ← = MOLO-HRDW
├── data/              MOLONARI-data       ← = MOLO-DATA
└── pyheatmy/          MOLONARI-computo    ← = MOLO-CMPT
```

A subtwin is installed on its own (`~/.cgs/MOLO-HRDW-…`) and inside MOLO-TWX
(`~/.cgs/MOLO-TWX-…/hardware`). Both are checkouts of the **same repository on the same
branch**, `CGS-MOLO`. What you push from one, the other pulls. You work on the smallest
twin that holds your change, and you only need rights on that one.

## 2. Look before you change

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs DEV login MOLO-HRDW fetch
```

`fetched=4`: every repository of the twin is up to date with GitHub. `commit` and `push`
then print the twin as a tree: every repository, its branch, and whether it is level with
GitHub (`[ALIGNED]`).

## 3. Change, commit, push

Make your change in the subtwin's repository (`~/.cgs/MOLO-HRDW-<timestamp>/`). On the
first run there is one waiting: the install added the gate's folders to
MOLONARI-hardware's `.gitignore`. Then:

```bash
pixi run cgs DEV login MOLO-HRDW commit "MOLO-HRDW under @cgs: the gate mounts are ignored"
pixi run cgs DEV login MOLO-HRDW push
```

```text
committed MOLO-HRDW: 772530e502a43d6e15330bd8d86b103214bf865c
…
memory_fold branch=ComplexGitSync_MOLO-HRDW_CGS-MOLO committed=True recorded=6
pushed MOLO-HRDW: origin/CGS-MOLO (+1)
{ "layer": "DEV", "code": "1000", … "agent_keys": 4, "cgitsync": 0, "closed": true }
```

Two things were pushed, each with its own key from your GLYPH:

- your commit, to MOLONARI-hardware `CGS-MOLO` (your DEV key on that repository);
- the twin's new state, to its memory branch (`memory_fold`, your DEV key on `.memory`).
  This is how a twin stays deterministic: every state it reaches is recorded.

**Write the message on one line, without `'`.** Pixi passes it between single quotes;
an apostrophe breaks the command (`failed to parse shell script`).

## 4. See it in the twin that contains it

In MOLO-TWX, `hardware/` is the same repository:

```bash
cd ~/.cgs/MOLO-TWX-<timestamp>/.atcgs
pixi run cgs <PROFILE> login MOLO-TWX pull
```

`hardware/` is then at `772530e`, your commit. (On 2026-11-05 MOLO-TWX was installed
just after the push and came with it directly.) Reading MOLO-TWX needs rights on
MOLO-TWX: being a DEV on MOLO-HRDW gives none there. A user who must see everything is
admitted on MOLO-TWX as USR on its repositories.

## 5. What the gate kept you from

- **Writing the gate or the published identities.** Your keys on atCGS and
  `.omniscience` are read-only on GitHub.
- **Working on another twin.** Your grants are in MOLO-HRDW's register only.
- **Admitting anyone.** `enrol`, `admit`, `publish` and `promote` are OPX verbs.
- **Using someone else's keys, or your own `~/.ssh`.** Each command loads only your GLYPH's
  keys, and offers each repository its own key.

## Good to know

- **The commit's author is your machine's git identity** (`git config user.name`), not
  your atCGS UID: atCGS decides who may push, it does not sign commits.
- **Your `.memory` key opens the whole memory repository,** which holds the memory branch
  of every twin. Registers are signed by OPX, so a tampered one is refused, but other
  branches could be written: treat that key with care.

## If something goes wrong

| You see | Why | Do |
|---|---|---|
| `failed to parse shell script … Expected closing single quote` | a `'` in the message | write it without `'` |
| `pushed=0 … already level with its upstream` | nothing committed (the commit failed or was skipped) | read the commit's output, commit again |
| `DEV may not run 'tag' through login; DEV runs: …` | an operation your profile does not have | the list is in the message; README § 3 |
| `Permission denied (publickey)` on push | your deploy key is not installed, or is read-only | ask OPX (TUTO 02 § 6) |

# TUTO 02 — The four levels and the OpFrontier

**Goal:** ask `@cgs` for a level's outgoing transition, know which commands each
level may run, and know what the OpFrontier does and does not do.

**Scope.** The OpFrontier here is a *table of allowed transitions* plus a
command gate. It does not move data itself; `cgitsync` does.

## 1. The four levels

The levels and their codes come from ComplexGitSync (`op_levels.py`); README § 3 has
the table. OPX is POE (`0000`).

## 2. The three transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

Each row reads: source artifact, source level, destination level, destination
artifact. PUB is terminal. There is no fourth transition.

## 3. Ask for a transition

```bash
pixi run '@cgs' OPX
```

Real output (abridged):

```json
{ "layer": "OPX", "transition": [".gts", "OPX", "DEV", ".cgs"], "evidence": "unverified" }
```

Run the same with `DEV` and `USR` to see the other two rows. `PUB` prints the
public view instead:

```bash
pixi run '@cgs' PUB
```

`"evidence": "unverified"` is the only value a transition can carry today. No
verifier exists, so nothing is ever reported as verified.

## 4. Which selectors are accepted

`@cgs` accepts exactly four selectors: `OPX`, `DEV`, `USR`, `PUB`. Anything else is
refused with exit code 2. A selector followed by an argument must match one of the
forms below; anything else is refused.

| Form | Example | Needs `ATCGS_AUTHORIZE` |
|---|---|---|
| no argument | `@cgs DEV` | no |
| a public mount | `@cgs USR .omniscience` | no |
| a private mount | `@cgs DEV .cgitsync` | yes, OPX and/or DEV |
| identity verb | `@cgs OPX init`, `@cgs DEV request …`, `@cgs DEV login TWIN …` | depends on verb (see TUTO 03) |
| a cgitsync verb | `@cgs DEV status` | yes |

`ATCGS_AUTHORIZE` names the private levels the operator grants, for example
`ATCGS_AUTHORIZE=DEV pixi run '@cgs' DEV status`. A level may be granted only if it
is OPX or DEV, and USR never has a private mount.

## 5. Mounts

Public and private mounts are described by `ATCGS_MOUNTS`, a TOML file of
`[[mount]]` entries with a pinned commit. Without that variable, every mount
answers `"evidence": "unavailable"`:

```bash
pixi run '@cgs' USR .omniscience
# {"mount": ".omniscience", "evidence": "unavailable"}
```

## 6. What the gate does

- `login` (TUTO 03) allows a fixed list of cgitsync verbs per level. A verb outside
  the list is refused before anything runs.
- The layer a command is run as decides the list. A USR login cannot push.
- The remote enforces the rest: a DEV key cannot push to a repo it is not granted.

## 7. What is not built

- No transition moves artifacts between levels. `cgitsync` does the work.
- No evidence is ever `verified`.
- Only a bare `login TWIN bootstrap` runs the command ComplexGitSync's `LevelCommand`
  names (`bootstrap <twin>-<level>.cgs`); every other verb runs as given.

## 8. Definition of done for this tutorial

- `pixi run '@cgs' OPX` prints the `.gts OPX DEV .cgs` transition.
- You can list which selectors are accepted, and which forms need `ATCGS_AUTHORIZE`.
- You can explain why `"evidence": "unverified"` is the only value you will see.

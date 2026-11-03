# TUTO 01 — The BIOS declaration

**Goal:** read the BIOS section of `spec/contracts.toml`, run the check that
validates it, and understand what it does and does not do.

**Scope.** The BIOS is a declaration. Nothing boots from it. This tutorial covers
the file, the check, and the one sentence you need about each symbol.

## 1. Where it lives

`spec/contracts.toml`, the `[boot]` and `[bios_history]` tables, and the
fixtures in `scripts/contract_check.py` that they must match.

## 2. Run the check

```bash
pixi run contract-inspect
```

Expected output (the counts are the ones this check reports):

```text
"status": "VALIDATED_SYNTAX",
"version": "1.7.1-alpha",
"bios_new_rows": 5,
"bios_history_rows": 7,
"history_extended_rows": 2,
```

A changed row makes the command exit with `CONTRACT_REFUSED: noncanonical boot.current`
(or the matching section name). The check compares rows in order.

## 3. Read the four lines of `[boot]`

```toml
[boot]
identity = ["atCGS", "ALPHA", "BIOS", "ComplexGitSync", "M.m.p"]
current = [
 ["ComplexGitSync", "G", "POEX", ".gts"],
 [".gts", "G", "OPX", "TWX"],
 ["TWX", "ENV", "HWX", "DEV"],
 ["DEV", "HWX", "TWX", "USR"],
 ["USR", "TWX", "G", ".cgs"],
]
```

Each row has four fields, in this order: **source, edge, interface, target**.
`identity` is the header. It says which product this is, and the engine version
to pin. `M.m.p` is a placeholder: no installed version is claimed.

## 4. What each symbol means today

| Symbol | Status | What it stands for in the software |
|---|---|---|
| `ComplexGitSync` | implemented | the engine, installed by `pixi.toml` at the pinned revision |
| `G` | declared | the prime graph, `{NAME, NODE, EDGE, OP}` |
| `.gts` | implemented | a ComplexGitSync state file |
| `OPX`, `DEV`, `USR`, `PUB` | implemented | the four levels, from `op_levels` |
| `.cgs` | implemented | the tree-description file cgitsync reads |
| `POEX` | **removed** | the 1.5 proof-of-existence microcode; see README § 7 |
| `TWX` | placeholder | no code reads it |
| `ENV` | placeholder | no code reads it |
| `HWX` | placeholder | no code reads it |

Row 1 names `POEX`, which no longer exists. The row is kept because the check
requires it. Changing the row requires changing the fixture in the same commit.

## 5. Read the history

`[bios_history]` holds seven earlier rows and two extension rows. They are kept
as written. The check verifies their form. No code uses them.

## 6. What the BIOS does not do

- It does not start a process, read a file at start-up, or select a level.
- It does not prove identity. The `BOOT` symbol in the history names a step, not
  an authenticated proof.
- It does not check that `TWX`, `ENV` or `HWX` exist.

The working entry points are `pixi run '@cgs' <LAYER>` (TUTO 03) and the identity
commands (TUTO 05).

## 7. Definition of done for this tutorial

- `pixi run contract-inspect` prints `VALIDATED_SYNTAX`.
- You can name what each symbol in § 4 refers to, and which ones are placeholders.
- You know that changing a row without the fixture fails the check.

# TUTO 02 — PRIME G, and the DELTA / NABLA rows

**Goal:** know what the PRIME G tuple and the DELTA/NABLA rows are in the software,
and what checking them proves.

**Scope.** PRIME G is a four-field naming scheme. The DELTA/NABLA rows are declared
text. Neither drives any operation today.

## 1. PRIME G

`PRIME G = {NAME, NODE, EDGE, OP}`: four ordered fields. Each field is itself a
graph, and each answers one question:

| Field | Question |
|---|---|
| NAME | what exists |
| NODE | what identity state it is in |
| EDGE | what its universal interface is |
| OP | which mutation it performs |

Two places state it:

- `spec/contracts.toml`: `prime_g = ["NAME", "NODE", "EDGE", "OP"]`, checked by `contract-inspect`.
- `atcgs/__init__.py`: `PRIME_G = ("NAME", "NODE", "EDGE", "OP*")`, checked by one test.

**Known mismatch.** The code writes `OP*`; the contract writes `OP`. The star marks
a requestable operation in the prose, but no code uses the tuple at run time. Pick one
spelling and change both places together. Until then, both checks pass because each
compares against its own copy.

## 2. The DELTA / NABLA rows

`spec/contracts.toml` declares four rows, `[delta_nabla] sequence`:

```text
DELTA POEX NABLA OPX
OPX   ENV  PRIME DELTA
DELTA ENV  PRIME NABLA
NABLA EDGE POEX  OPX
```

What the software does with them:
- `contract-inspect` checks that the rows match `scripts/contract_check.py`.
- `POEX` appears in them, but the POEX microcode was removed in 1.6.0 (README § 7).
- `ENV` and `PRIME` have no code.
- `OpFrontier.serve_poex()` returns the static descriptor `("POEX", "NODE", "DELTA", "OPX")`.
  It executes nothing; a test checks the tuple.

So DELTA and NABLA are names in a declared chain. They have no operation behind them.

## 3. Run the checks

```bash
pixi run contract-inspect       # "delta_nabla_rows": 4, the row form only
pixi run test                    # tests/test_opfrontier_poex.py, tests/test_contracts.py
```

## 4. What is not built

- No operation computes DELTA or NABLA.
- No key derivation uses DELTA. The class KEY of TUTO 05 is held by OPX and keyed
  by the identity, not by DELTA.
- Nothing checks that `ENV`, `PRIME` or `DELTA` refer to a real object.

## 5. Definition of done for this tutorial

- You can state the four PRIME G fields and their questions.
- You can say which of the two spellings (`OP`, `OP*`) each file uses, and that they
  must be made equal.
- You can say that the DELTA/NABLA rows are checked as text and used by no code.

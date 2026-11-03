# TUTO 04 — POEX (removed in 1.6.0)

**Status: this tutorial describes removed code. None of its commands run.**

It is kept as a record of the 1.5.0-alpha design, last present at commit
`4e3ec5e` (subject `cgs-1.5.0-alpha`). Use `git show 4e3ec5e:TUTOS/TUTO_04_POEX.md`
to read the full original.

## What it was

- A 256×256-bit matrix, 8 192 bytes, split into 64 packets of 4×256 bits.
- A proof of existence that compared two such matrices (GLYPHs) by XOR and counted
  zeros. Equal means all 65 536 bits matched.
- Implemented in two C microcodes, `poex` (comparison) and `eopx` (SEED to GLYPH),
  wrapped by `atcgs.POEX` and `atcgs.EOPX`.

## Why it was removed

The GLYPH was derived from a secret SEED, so proving identity meant sending that
secret. A zero count proves no identity, and the register stored names. See
README § 7 and TUTO 05 for what replaced it.

## What survives

- The 256×256-bit size: the GLYPH is still 8 192 bytes.
- The 4-bit codes: they are now the level codes of README § 3.
- The `POEX` symbol in `spec/contracts.toml`, kept because the BIOS check requires it
  (TUTO 01 § 4).

## Definition of done for this tutorial

- You know the tutorial is historical, and where the last working state is.
- You can find the replacement in TUTO 05.

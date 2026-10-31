# TUTO 05 — README, USR / PUB, GLYPH and KEY

**Goal:** integrate the five publication tuples and the KEY prototype without alteration.

## 1. New canonical frontier

```text
README atCGS USR PUB
GLYPH POEX PUB DELTA
DELTA POEX OPX HASH
HASH DELTA CGS OPX
.cgs USR PUB .toml
```

These are five `NAME NODE EDGE OP` records.
`.wth` no longer exists; no tuple may reintroduce it.

## 2. Link with the earlier transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

The new table and the OpFrontier table serve distinct purposes.
Do not merge their fields to build five-column tuples.
Do not create an artificial fourth OpFrontier transition.

## 3. The GLYPH and the class KEY

The GLYPH (`.bit`) is the 256×256 public key of DELTA.
It is a POEX privilege and is never exposed.
POE is reached only through its hash, the prototype of the class KEY:

```text
PUB DELTA POEX KEY
KEY OPX CGS PUB
KEY sha256(GLYPH)
```

The first two lines are `NAME NODE EDGE OP` records.
The third is a definition, `KEY := sha256(GLYPH)`, not a tuple.
The simulator treats 256×256 bits as 8 192 bytes, row by row.
The lab file is synthetic: it is not a real GLYPH.

## 4. POEX, the wallet

The wallet is the Python class `atcgs.POEX`; it wraps the C `poex` microcode.
For a NAME X, POEX asks one question only: does X exist in PoE?

```text
NAME GLYPH POEX OPX
NAME GLYPH PUB .toml
```

If not, POEX launches the GLYPH integration:

1. Ask a SEED: a square `.bit` of at least 256×256 bits.
2. `GLYPH := shake_256(hash(SEED) + SEED)`, 256×256 bits, deterministic.
3. The microcode frames the GLYPH; OPX registers `NAME -> (hash(SEED), hash(GLYPH))`.

If yes, the request is an OpFrontier request ComplexGraphSync -> ComplexGitSync.
POEX then delivers `.poe`, one 4×256-bit POEX packet:

```text
OPX  hash(GLYPH)        OPX only
DEV  hash(DEV ssh key)  temporary, destroyed after the request
USR  hash(NAME)
PUB  hash(SEED)         unique ID of NAME
```

Each layer receives only its own slot.
Only `hash(SEED)` crosses the frontier; the GLYPH is never stored, by anyone.
The compression runs even on a 256×256 SEED, so `hash(GLYPH) != hash(SEED)`.
The DEV key uses the `ssh-keygen` core of [sshKeyGen](https://github.com/flipoyo/sshKeyGen).

```text
.cgitsync      PRIVATE  (ComplexGitSync)
.omniscience   PUBLIC   (ComplexGraphSync)
```

No tuple is a declaration of access rights.
The internal Omniscience register does not become PUBLIC without a projection.

## 5. Inspect the new table

```bash
pixi run contract-inspect
```

Expected result: `public_rows = 5`, `key_rows = 2` and `glyph_rows = 2`.
The comparison is strict, field by field.
A KEY not defined as `sha256(GLYPH)`, or not held by POEX, is refused.

## 6. Generate an unpublished manifest

```bash
pixi run poex-candidate
pixi run contract-candidate
```

The candidate must keep `poex_verified=false` and `NOT_PUBLISHED`.
The script does not contact the PUBLIC domain and writes nothing to GitHub.
The manifest contains only the commitment, the sizes and the status.
It must never carry the raw 8 192 bytes of a GLYPH.

## 7. Negative test

In a copy of the manifest, replace `poex_verified` with `true`.
The `candidate` validator must refuse this unjustified promotion.
An exact local result is not an authenticated checkpoint.

## 8. Outlook

`hash` is `sha256`; the compression is `shake_256`, seeded by `hash(SEED)`.
`atcgs.POEX` runs the flow; no `@cgs` selector calls it yet.
The OPX register is passed to POEX; where OPX persists it is still open.

## 9. Definition of success

The five tuples, the two KEY and the two GLYPH records are strictly preserved and checkable.
The 256×256 matrix sequences correctly into 64 packets.
No GLYPH and no `.PRIVATE` is exposed as a validated public answer.
Tutorial 06 gathers the checks and the 24 h schedule.

## Additional validation: cases to automate

- Tuple 0: `README` NAME, `atCGS` NODE, `USR` EDGE, `PUB` OP.
- Tuple 1: `GLYPH` NAME, `POEX` NODE, `PUB` EDGE, `DELTA` OP.
- Tuple 2: `DELTA` NAME, `POEX` NODE, `OPX` EDGE, `HASH` OP.
- Tuple 3: `HASH` NAME, `DELTA` NODE, `CGS` EDGE, `OPX` OP.
- Tuple 4: `.cgs` NAME, `USR` NODE, `PUB` EDGE, `.toml` OP.
- Every tuple: refuse swapped, deleted or case-normalised fields.
- Every tuple: no implicit PRIVATE permission.
- KEY: `PUB DELTA POEX KEY` and `KEY OPX CGS PUB` unchanged; KEY is `sha256(GLYPH)`.
- GLYPH: `NAME GLYPH POEX OPX` and `NAME GLYPH PUB .toml` unchanged.
- SEED: refuse a non-square `.bit` or one under 256×256 bits.
- `hash(SEED)`: refuse a SEED already registered under another NAME.
- GLYPH: never stored, never in a candidate, a `.poe` or a public answer.
- DEV key: destroyed after the OpFrontier request, even when it fails.
- Publication: check a signed checkpoint, an anchored identity, no local paths.
- An `.omniscience` field does not publish a proof by magic.
- PRIVATE content must remain inaccessible to PUB.
- The matrix is binary, not a PNG; extensions are literal identifiers.
- The interface must report `NOT_PUBLISHED` unambiguously.

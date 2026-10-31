# TUTO 05 — README, USR / PUB, .bit and .wth

**Goal:** integrate the five publication tuples without alteration.

## 1. New canonical frontier

```text
README atCGS USR PUB
PUB 256 256 .bit
.bit .computo .omniscience .wth
.wth .computo .gts .cgs
.cgs USR PUB .toml
```

These are five `NAME NODE EDGE OP` records.
The two `256` must never be deduplicated.
The `.wth` extension is opaque, with no serialiser defined here.

## 2. Link with the earlier transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

The new table and the OpFrontier table serve distinct purposes.
Do not merge their fields to build five-column tuples.
Do not create an artificial fourth OpFrontier transition.

## 3. The `.bit` representation

The symbol `PUB` associates the dimensions 256 and 256 with `.bit`.
The simulator treats 256×256 bits as 8 192 bytes, row by row.
The `.bit` field alone does not prove the GLYPH's authenticity.
The lab file is not a signed artistic object.

## 4. Two spaces and one engine

```text
.computo       PRIVATE  (ComplexGraphSync)
.omniscience   PUBLIC   (ComplexGraphSync)
.cgitsync      INTERNAL (ComplexGitSync)
```

No tuple is a declaration of access rights.
The exact semantics of `.wth` must be specified separately.
The internal Omniscience register does not become PUBLIC without a projection.

## 5. Inspect the new table

```bash
pixi run contract-inspect
```

Expected result: `public_rows = 5`.
The comparison is strict, including the repetition of `256`.

## 6. Generate an unpublished manifest

```bash
pixi run poex-candidate
pixi run contract-candidate
```

The candidate must keep `poex_verified=false` and `NOT_PUBLISHED`.
The script does not contact the PUBLIC domain and writes nothing to GitHub.
The manifest contains only the commitment, the sizes and the status.
It must never carry the raw 8 192 bytes by default.

## 7. Negative test

In a copy of the manifest, replace `poex_verified` with `true`.
The `candidate` validator must refuse this unjustified promotion.
An exact local result is not an authenticated checkpoint.

## 8. Outlook for `.wth`

The protocol must still specify the meaning of the three associated fields.
A file format, a routing operation and an address type
cannot be deduced from four letters and a leading dot.

## 9. Definition of success

The five tuples are strictly preserved and checkable.
The `.bit` matrix sequences correctly into 64 packets.
No PRIVATE content is exposed as a validated public answer.
Tutorial 06 gathers the checks and the 24 h schedule.

## Additional validation: cases to automate

- Tuple 0: `README` stays NAME.
- Tuple 0: `atCGS` stays NODE.
- Tuple 0: `USR` stays EDGE.
- Tuple 0: `PUB` stays OP.
- Tuple 0: refuse swapping the last two fields.
- Tuple 0: refuse deleted fields.
- Tuple 0: refuse case normalisation.
- Tuple 0: no implicit PRIVATE permission.
- Tuple 1: `PUB` stays NAME.
- Tuple 1: `256` stays NODE.
- Tuple 1: `256` stays EDGE.
- Tuple 1: `.bit` stays OP.
- Tuple 1: refuse swapping the last two fields.
- Tuple 1: refuse deleted fields.
- Tuple 1: refuse case normalisation.
- Tuple 1: no implicit PRIVATE permission.
- Tuple 2: `.bit` stays NAME.
- Tuple 2: `.computo` stays NODE.
- Tuple 2: `.omniscience` stays EDGE.
- Tuple 2: `.wth` stays OP.
- Tuple 2: refuse swapping the last two fields.
- Tuple 2: refuse deleted fields.
- Tuple 2: refuse case normalisation.
- Tuple 2: no implicit PRIVATE permission.
- Tuple 3: `.wth` stays NAME.
- Tuple 3: `.computo` stays NODE.
- Tuple 3: `.gts` stays EDGE.
- Tuple 3: `.cgs` stays OP.
- Tuple 3: refuse swapping the last two fields.
- Tuple 3: refuse deleted fields.
- Tuple 3: refuse case normalisation.
- Tuple 3: no implicit PRIVATE permission.
- Tuple 4: `.cgs` stays NAME.
- Tuple 4: `USR` stays NODE.
- Tuple 4: `PUB` stays EDGE.
- Tuple 4: `.toml` stays OP.
- Tuple 4: refuse swapping the last two fields.
- Tuple 4: refuse deleted fields.
- Tuple 4: refuse case normalisation.
- Tuple 4: no implicit PRIVATE permission.
- Publication: check a signed checkpoint.
- Publication: check the explicitly authorised data.
- Publication: check that local paths are rejected.
- Publication: check the candidate/public distinction.
- Publication: check filtered repository URLs.
- Publication: check minimal answer fields.
- Publication: check an anchored identity.
- Publication: check an independent root.
- The name `.wth` is opaque in 0.1.1-alpha.
- An `.omniscience` field does not publish a proof by magic.
- The repeated 256 is fixed by contract.
- PRIVATE content must remain inaccessible to PUB.
- The candidate output contains no secret key.
- A real checkpoint must be authenticated.
- Recent tuples do not replace the engine's `.cgs` grammar.
- The matrix is binary, not a PNG.
- The candidate root is not a global record.
- The interface must report `NOT_PUBLISHED` unambiguously.
- Extensions are literal identifiers.

# TUTO 03 — System Layers and OpFrontier

**Goal:** distinguish access API, orchestration and PUBLIC projection.

## 1. Four System Layers

```text
PRIME CGS = {OPX, DEV, USR, PUB}
```

`OPX`: operational frontier, authorised private processing.
`DEV`: development operations subject to the engine's protections.
`USR`: requesters, authenticated or not according to the access policy.
`PUB`: controlled presentation of a publishable result.

These are not four rewrites of ComplexGitSync.
These are not the numeric levels of the former Ring annotations.

## 2. The three canonical transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

Each transition has exactly four fields.
There are **three transitions**, not an implicit fourth one.
These quadruples are descriptions, never automatic `cp` commands.

## 3. Separation of spaces

```text
PUBLIC  = .omniscience
PRIVATE = .cgitsync
```

`.omniscience` is the ComplexGraphSync PUBLIC domain.
`.cgitsync` is the PRIVATE one: the ComplexGitSync mount, its operational memory.
`.computo` no longer exists; it is `.cgitsync`.

## 4. Role of OpFrontier

Validate a selector and a transition.
Preserve the native Merkle identity of existing `.gts`.
Have mutations executed by the engine's authorised APIs.
Refuse the PUBLIC emission of a raw PRIVATE tree.
Emit an unverified result when a checkpoint is missing.

## 5. The `@cgs` interface

```bash
# Without argument: emits the outgoing transition; PUB serves the PUBLIC view.
pixi run '@cgs' OPX
pixi run '@cgs' DEV
pixi run '@cgs' USR
pixi run '@cgs' PUB
```

Raw `cgitsync` verbs are refused at top level (exit code 2).
`OPX`/`DEV` delegate them only with `ATCGS_AUTHORIZE` (otherwise exit code 3).

## 6. Roles of proofs

The PoE vector may limit the exposed fields.
It is not an authentication policy.
`TreeProfile.USER/DEV` derives from the GitTree configuration, not from an ACL.
Rights must be decided at each frontier of the PUBLIC server.

## 7. Tuple verification

```bash
pixi run contract-inspect
```

The report must confirm `opfrontier_rows = 3`.
Changes of case, order or field must be refused.

## 8. Security scenarios

A `USR` request cannot write to `.cgitsync` by default.
The `PUB` answer must not include infrastructure secrets.
A valid hash does not certify the scope of rights.
A missing proof is different from a forged proof.
A deleted repository may be unavailable without historical invalidity.

## 9. Exit criterion

Three immutable transitions are described and verified.
The procedure performs no Git mutation.
The PUBLIC frontier is not considered in service.
Tutorial 04 tests the 4×256 binary stream.

## Additional validation: cases to automate

- Transition 1: declared input `.gts`.
- Transition 1: exact source layer `OPX`.
- Transition 1: exact destination layer `DEV`.
- Transition 1: exact output `.cgs`.
- Transition 1: an inversion must fail.
- Transition 2: declared input `.cgs`.
- Transition 2: exact source layer `DEV`.
- Transition 2: exact destination layer `USR`.
- Transition 2: exact output `.toml`.
- Transition 2: an inversion must fail.
- Transition 3: declared input `.toml`.
- Transition 3: exact source layer `USR`.
- Transition 3: exact destination layer `PUB`.
- Transition 3: exact output `.omniscience`.
- Transition 3: an inversion must fail.
- OPX: check explicit authorised entry.
- OPX: check PRIVATE access refused without rights.
- OPX: check rejection of the lowercase name.
- OPX: check no raw proxy.
- OPX: check proof state respected.
- OPX: check no internal path leak.
- OPX: check no public mutation.
- DEV: check explicit authorised entry.
- DEV: check PRIVATE access refused without rights.
- DEV: check rejection of the lowercase name.
- DEV: check no raw proxy.
- DEV: check proof state respected.
- DEV: check no internal path leak.
- DEV: check no public mutation.
- USR: check explicit authorised entry.
- USR: check PRIVATE access refused without rights.
- USR: check rejection of the lowercase name.
- USR: check no raw proxy.
- USR: check proof state respected.
- USR: check no internal path leak.
- USR: check no public mutation.
- PUB: check explicit authorised entry.
- PUB: check PRIVATE access refused without rights.
- PUB: check rejection of the lowercase name.
- PUB: check no raw proxy.
- PUB: check proof state respected.
- PUB: check no internal path leak.
- PUB: check no public mutation.
- Frontier .gts → .cgs: no automatic publication.
- Frontier .cgs → .toml: no automatic publication.
- Frontier .toml → .omniscience: no automatic publication.
- An external request cannot force `level=PUBLIC`.
- No permission is deduced from a layer's index.
- Public reading mutates no GitRepo.
- The engine keeps its own locks and checks.
- The PUBLIC projection redacts paths and secret identifiers.
- The presence of a root does not prove a repo's availability.
- The three transitions remain ordered.
- The target `PUB` can answer without a private bootstrap.

# atCGS — ComplexGraphSync 0.1.1-alpha

**Canonical README — USR / PUB / BIOS / POEX / OpFrontier.**

This repository describes a local executable prototype, not a deployed PUBLIC service.
It keeps the ComplexGitSync engine and materialises the CGS frontiers.
Goal: a falsifiable, reproducible and minimal architecture within 24 h.

## 1. PRIME G invariant

`PRIME G = {NAME, NODE, EDGE, OP}`: exactly four ordered fields.
Names, extensions, repetitions and capitalisation are part of the contract.
`*G` denotes a requestable OperatingSpace, not an already verified answer.

## 2. New README / USR / PUB frontier

```text
README atCGS USR PUB
GLYPH POEX PUB DELTA
DELTA POEX OPX HASH
HASH DELTA CGS OPX
.cgs USR PUB .toml
```

These five lines are PRIME G tuples, kept without normalisation.
The GLYPH (`.bit`) is the 256×256 public key of DELTA: a POEX privilege, never exposed.
POE is reached only through `KEY := sha256(GLYPH)`, the prototype of the class KEY:

```text
PUB DELTA POEX KEY
KEY OPX CGS PUB
KEY sha256(GLYPH)
```

POEX is the wallet, the Python class `atcgs.POEX`; it wraps the C `poex` microcode.
For a NAME X it asks one question, "does X exist in PoE?", then delivers `.poe`:

```text
NAME GLYPH POEX OPX
NAME GLYPH PUB .toml

X not in PoE  ask SEED: a square .bit of at least 256x256 bits
              GLYPH := shake_256(hash(SEED) + SEED), 256x256 bits
              OPX registers NAME -> (hash(SEED), hash(GLYPH))
X in PoE      OpFrontier request ComplexGraphSync -> ComplexGitSync
.poe          (OPX, DEV, USR, PUB) = one 4x256-bit POEX packet
              hash(GLYPH), hash(DEV ssh key), hash(NAME), hash(SEED)
```

`hash(SEED)` is the unique ID of NAME, and the only value crossing the frontier.
The pair `(hash(SEED), hash(GLYPH))` is known by OPX only.
POEX never stores the GLYPH, and nobody does; `.omniscience` and `.computo` report only its hash.
The compression always runs, so `hash(GLYPH)` never equals `hash(SEED)`.
The DEV ssh key is temporary: it uses the `ssh-keygen` core of
[sshKeyGen](https://github.com/flipoyo/sshKeyGen) and is destroyed after the request.
`.computo` belongs to the PRIVATE domain of ComplexGraphSync.
`.omniscience` denotes its PUBLIC frontier, limited to publishable proofs.
Character strings are not implicit execution commands.

## 3. BIOS / BOOT

```text
atCGS ALPHA BIOS ComplexGitSync M.m.p
ComplexGitSync G POEX .gts
.gts G OPX TWX
TWX ENV HWX DEV
DEV HWX TWX USR
USR TWX G .cgs
```

The first line is the boot identity and the engine version to pin.
`M.m.p` is a placeholder: do not invent an installed version.
The next five lines are strict four-field tuples.
`ENV`, `HWX`, `TWX` are kept as symbols until they are specified.
`BOOT` does not mean an authenticated proof of existence.

## 4. System Layers and OpFrontier

```text
PRIME CGS = {OPX, DEV, USR, PUB}
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

The four System Layers are not four Git engines.
The three four-field frontiers authorise no automatic copy.
`OPX` and `DEV` remain bound to authorised private operations.
`USR` expresses the request; `PUB` limits what may be made public.
The `@cgs` decorator accepts only these four selectors (ALPHA.md).
The historical `cgitsync` CLI remains internal and autonomous.

## 5. POEX — transport of 256×256 bits

```text
Matrix = 256 rows × 256 bits = 65 536 bits = 8 192 bytes
Packet = 4 rows × 256 bits = 1 024 bits = 128 bytes
Stream = 64 indexed packets, in ascending row-major order
.poe   = one zero-count report per 4-bit quartet
Total  = 16 384 reports; 256 reports per packet
```

The zero counter proves neither identity nor existence at a given instant.
The Merkle root of POEX packets is distinct from the GitTree MerkleRoot.
A single-bit change, a permutation or a missing packet is rejected.
The last quartet is kept logically; no Rust pointer is simulated.

## 6. Spaces and publication

```text
ComplexGraphSync PRIVATE = .computo
ComplexGraphSync PUBLIC  = .omniscience
ComplexGitSync INTERNAL  = .cgitsync
```

A candidate manifest is not an authenticated checkpoint.
No public output contains a secret, a private path or a raw GitTree.
The former internal PRIVATE Omniscience register is not forcibly made public.
A local success does not mean publication on a network.

## 7. Starting the offline lab

Requirements: Pixi only; every command below is a Pixi task (pixi install once).
From the root of the atCGS checkout:

```bash
pixi run contract-inspect
pixi run poex-candidate
pixi run contract-candidate
pixi run test
```

The `inspect` option validates the tuples of `spec/contracts.toml`.
The sequencer uses a deterministic demonstration matrix by default.
`candidate` must display `NOT_PUBLISHED` and `poex_verified=false`.
None of it bootstraps a tree or accesses a real `.computo`.

## 8. TUTORIALS, 150 lines each

- [TUTO 01 — BIOS / BOOT](TUTOS/TUTO_01_BIOS_BOOT.md)
- [TUTO 02 — PRIME G and DELTA/NABLA](TUTOS/TUTO_02_PRIME_G.md)
- [TUTO 03 — System Layers and OpFrontier](TUTOS/TUTO_03_OPFRONTIER.md)
- [TUTO 04 — POEX 4×256](TUTOS/TUTO_04_POEX.md)
- [TUTO 05 — USR / PUB, GLYPH and KEY](TUTOS/TUTO_05_USR_PUB.md)
- [TUTO 06 — Integration and 24 h roadmap](TUTOS/TUTO_06_INTEGRATION.md)

## 9. Upstream code reality

`atCGS` PR #1 (merged) relayed several raw `cgitsync` commands.
They are now refused outside an authorised `OPX`/`DEV` selector.
`ComplexGitSync` provides the GitTree / State / Memory / Integrity engine.
The package tutorials are reproducible examples, not a merged PR.

## 10. ALPHA release criteria

- [ ] The five README/USR/PUB tuples are unchanged.
- [ ] The six new BIOS symbols keep their original order.
- [x] The four System Layers are the only exposed `@cgs` entries.
- [ ] The cryptographic packet proof verifies independently.
- [ ] PRIVATE access is never promoted by the PoE level.
- [ ] `.omniscience` serves only authorised and authenticated proofs.
- [ ] ComplexGitSync schema-1 Merkle compatibility is preserved.
- [ ] CI tests document failures, not only successes.

## 11. Tracking

ComplexGitSync #193: https://github.com/flipoyo/ComplexGitSync/issues/193
atCGS #2: https://github.com/flipoyo/atCGS/issues/2
atCGS PR #1: https://github.com/flipoyo/atCGS/pull/1

**Status: documentation model and offline demonstrator; no verified PUBLIC BOOT.**

## Additional validation: cases to automate

- Every PUBLIC answer requires an explicit publication policy.
- Never infer a Git clone from a tuple symbol.
- A requestable name does not mean an available service.

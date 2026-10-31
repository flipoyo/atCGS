# TUTO 06 — ALPHA integration and 24 h roadmap

**Goal:** run the lab end to end, without a fake release.

## 1. Active contracts

`BIOS` is a boot protocol still being formalised.
`PRIME G` fixes four strict fields per tuple.
`PRIME CGS` fixes the four layers OPX, DEV, USR, PUB.
`OpFrontier` describes three artifact transitions.
`POEX` sequences 256×256 matrices into 64 packets of 4×256.
The new tuples describe the README/USR/PUB frontier.

## 2. Engine and spaces

```text
ComplexGraphSync = interface and controlled public answer
ComplexGitSync = GitTree, Memory, State and Integrity engine
PUBLIC = .omniscience
PRIVATE = .computo
INTERNAL = .cgitsync
```

Do not reimplement the Git/Merkle engine in the decorator.
Do not turn a file suffix into a mutation order.

## 3. Offline demonstration

```bash
pixi run contract-inspect
pixi run poex-candidate
pixi run contract-candidate
pixi run test
```

The whole run produces a local report, not a real publication.
The outputs are reproducible in the pinned Pixi environment.

## 4. P0 roadmap

| Step | Window | Deliverable |
| --- | --- | --- |
| BIOS | H0–H4 | Freeze the tuples, version and identity |
| POEX | H4–H10 | Packets, Merkle, OpFrontier emitter |
| `@cgs` | H10–H16 | 4 System Layer selectors |
| Security | H16–H21 | Refusal of PRIVATE leaks and invalid proofs |
| Release candidate | H21–H24 | PR, CI tests and promotion decision |

This breakdown is a development target, not a time-bound promise.

## 5. Observed GitHub state

`atCGS` PR #1 is merged.
The decorator now accepts only the `OPX DEV USR PUB` selectors.
Real verification of `.omniscience` proofs remains to be implemented.
Validating this package modifies no GitHub repository.

## 6. Optionally run the former prototype

```bash
git clone --branch feature/alpha-pixi-opfrontier \
  https://github.com/flipoyo/atCGS.git
cd atCGS
pixi install
pixi run '@cgs' --help
pixi run test
```

This sequence requires Git, Pixi and a reachable network.
It is separate from the standalone Python lab in this folder.
Do not run `release freeze` on a real project without context.

## 7. Validation criteria

Fixtures must preserve all fields and their positions.
POEX packets must be complete, ordered and reconstructible.
The candidate must stay `NOT_PUBLISHED` without a reliable checkpoint.
Publication must be independent of the internal GitTree's rights.
Integration must not modify historical schema-1 hashes.
The PR status must be observed, not guessed.

## 8. Out of scope

No forced switch from `.cgitsync` to `.computo`.
No remote GX4G service claimed to be operational.
No fictitious PoE signer or invented timestamp.
No data migration without documented proof and rollback.

## 9. Tracking

ComplexGitSync: https://github.com/flipoyo/ComplexGitSync/issues/193
atCGS: https://github.com/flipoyo/atCGS/issues/2
Prototype: https://github.com/flipoyo/atCGS/pull/1

The expected result is a controlled demonstrator, not a PUBLIC server.

## Additional validation: cases to automate

- H0–H4 BIOS: check exact fixture.
- H0–H4 BIOS: check reproducible output.
- H0–H4 BIOS: check non-zero exit on failure.
- H0–H4 BIOS: check no unauthorised access.
- H0–H4 BIOS: check test result recorded.
- H0–H4 BIOS: check achieved/simulated stage distinguished.
- H0–H4 BIOS: check the PR can be reviewed.
- H0–H4 BIOS: check engine dependency unchanged.
- H4–H10 POEX: check exact fixture.
- H4–H10 POEX: check reproducible output.
- H4–H10 POEX: check non-zero exit on failure.
- H4–H10 POEX: check no unauthorised access.
- H4–H10 POEX: check test result recorded.
- H4–H10 POEX: check achieved/simulated stage distinguished.
- H4–H10 POEX: check the PR can be reviewed.
- H4–H10 POEX: check engine dependency unchanged.
- H10–H16 @cgs: check exact fixture.
- H10–H16 @cgs: check reproducible output.
- H10–H16 @cgs: check non-zero exit on failure.
- H10–H16 @cgs: check no unauthorised access.
- H10–H16 @cgs: check test result recorded.
- H10–H16 @cgs: check achieved/simulated stage distinguished.
- H10–H16 @cgs: check the PR can be reviewed.
- H10–H16 @cgs: check engine dependency unchanged.
- H16–H21 Security: check exact fixture.
- H16–H21 Security: check reproducible output.
- H16–H21 Security: check non-zero exit on failure.
- H16–H21 Security: check no unauthorised access.
- H16–H21 Security: check test result recorded.
- H16–H21 Security: check achieved/simulated stage distinguished.
- H16–H21 Security: check the PR can be reviewed.
- H16–H21 Security: check engine dependency unchanged.
- H21–H24 Release candidate: check exact fixture.
- H21–H24 Release candidate: check reproducible output.
- H21–H24 Release candidate: check non-zero exit on failure.
- H21–H24 Release candidate: check no unauthorised access.
- H21–H24 Release candidate: check test result recorded.
- H21–H24 Release candidate: check achieved/simulated stage distinguished.
- H21–H24 Release candidate: check the PR can be reviewed.
- H21–H24 Release candidate: check engine dependency unchanged.
- Closing criterion: no invented proof of existence.
- Closing criterion: Merkle compatibility preserved.
- Closing criterion: no PRIVATE path exposed.
- Closing criterion: version resolution.
- Closing criterion: CI verified.
- Closing criterion: exact publication state.
- Test results are attached to the PR.
- Production commands are not launched by the lab.
- PRIVATE ACLs are evaluated separately.
- The release is blocked without attested publication.
- Historical schema-1 hashes remain unchanged.
- Cross-platform regressions remain to be checked.

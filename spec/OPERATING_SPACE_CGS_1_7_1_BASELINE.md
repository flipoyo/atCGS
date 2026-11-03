# Operating Space ontology — CGS-ALPHA baseline

Baseline verified 2026-11-03: atCGS `1.7.1-alpha` and ComplexGitSync `8.7.1` (`f56d8148cb4d484a228a9d8550c4e84fccdb9f19`).

Business tuple: `OperatingSpace = {TWIN, NODE, DATA, CMP}`. Physical NODE means HARDWARE or RIVERBED; it is not PRIME G's graph NODE and not a GitRepo. TWIN identities persist when instrumentation changes. DATA retains provenance and CMP references a versioned computation.

MemorySetupBranch: ComplexGitSync proposes a `.cgitsync/.memory` mount without `default_branch`; the effective branch is derived when loaded. atCGS mounts that private engine-owned memory in OPX and DEV. This is distinct from the public projection at `.omniscience`.

POC target: `flipoyo/MOLONARI1D` branch `CGS-ALPHA`, with six historic CGS-MOLO GitRepos plus atCGS. The four MOLO poles are logical Twins until the history-preserving four-GitRepo migration. No verified `.gts`, OPX publication or real physical-node registration is claimed.

See `spec/OPERATING_SPACE_TWIN_NODE_DATA_CMP.md` for normative domain semantics. This document does not modify executable `.cgs` grammar or GitTree hashes.

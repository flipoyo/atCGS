# atCGS — Operating Space domain ontology (CGS-ALPHA)

**Status:** design contract / declarative schema, not a new `.cgs` grammar or a deployed service.

```text
OperatingSpace = {TWIN, NODE, DATA, CMP}
```

This **domain-level** 4-tuple names the scientific/physical content operated through atCGS. Its four fields are ordered and have distinct types:

| Field | Definition | Invariant |
|---|---|---|
| `TWIN` | Persistent, requestable digital identity of an Operating Space or a nested space | Exists independently of a particular GitRepo, physical device or current State |
| `NODE` | Physical, identified object in the real world | Its permitted types include `HARDWARE` (sensor/instrument) and `RIVERBED` (physical riverbed); it is **not** a GitRepo |
| `DATA` | Observations, measurements, model inputs and derived results linked to an identified scope | References carry provenance and a State identity where available; raw data need not be PUBLIC |
| `CMP` | Computation, numerical model, processing or inference operating over DATA | A versioned computation is referenced separately from its inputs and results |

A `TWIN` may reference zero or more `NODE` objects, `DATA` assets and `CMP` operations; `NODE` does not have to be an instrument. A `RIVERBED` and the `HARDWARE` observing it retain separate identities. Moving/replacing a sensor does not rename the Sampling Point or the riverbed. Timestamped associations preserve history.

## Two ontological levels — must not be conflated

- **Infrastructure:** `PRIME G = {NAME, NODE, EDGE, OP*}`; each field of PRIME G is a Graph primitive. Its `NODE` is **not** the domain-level physical `NODE` introduced here.
- **Operating Space domain:** `{TWIN,NODE,DATA,CMP}`. It is a typed domain schema mapped onto an Operating Space managed by atCGS; the tuple is **not** an alternate PRIME G or an executable four-field `.cgs` statement.
- **GitTree and State:** ComplexGitSync (`CGS-ALPHA`) exclusively owns `.cgs`, `.gts`, memory, integrity and Merkle state.
- **Identity/activation:** atCGS (`CGS-ALPHA`) identifies the authorized user, activates TWIN, and configures repository access per role `{OPX,DEV,USR,PUB}`.

## Persistence and publication

The logical domain graph associates `TWIN → NODE`, `TWIN → DATA`, `TWIN → CMP`, plus `DATA → CMP → derived DATA` with typed, time-valid links. A TWIN identity may persist while these associations change.

`.omniscience` is the **registration/projection boundary**, not proof that registration happened. A future atCGS publication must: (1) authenticate an OPX-authorized request; (2) resolve a real, independently verified `.gts` State and provenance; (3) register TWIN/parent links and an allowlisted projection of physical-node references; (4) preserve PRIVATE sampling-site locations, login/key material and confidential DATA/CMP content. A `sha256(NAME)` lookup key alone is neither a Merkle proof nor authenticated PoE.

## MOLONARI reference integration

The first application lives at `flipoyo/MOLONARI1D` branch `CGS-ALPHA`, document `cgs-alpha/ONTOLOGY_TWIN_NODE_DATA_CMP.md`. Its root `MOLONARI` is a TWIN/Operating Space. The four **logical** poles `MOLO-HRDW`, `MOLO-DATA`, `MOLO-CMPT`, `MOLO-TWIN` remain registered Twin identities, not four migrated repositories. `Virtual Lab` and `Sampling Point` instances are also TWINs; a Sampling Point may link multiple physical NODEs. The initial seven-repository topology and historical `CGS-MOLO` branches stay unchanged until a separately validated migration.

## Minimal acceptance test for future executable implementation

1. Instantiate a MOLONARI Virtual Lab and a Sampling Point as separate, stable TWIN identities.
2. Link `RIVERBED-001` and `SENSOR-001` as distinct physical NODEs; attach temperature/pressure DATA and a versioned `pyheatmy` CMP.
3. Change the hardware linkage; assert Sampling Point and Riverbed identities remain unchanged and previous valid-time relations remain queryable.
4. Restore a verified GitTree State; only then register allowlisted TWIN references into `.omniscience`.
5. Demonstrate that PUB sees neither PRIVATE GitRepo content nor physical coordinates unless explicitly authorized for publication.

**Current milestone:** specification only. These tests are acceptance criteria, **not** assertions that runtime registration, State restoration or PUB proofs have been demonstrated.

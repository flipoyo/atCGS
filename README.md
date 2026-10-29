# @CGS

License: Apache-2.0

Version: ALPHA0001.00

Formal definition: [ComplexGraphSync](https://codeberg.org/gx4g/ComplexGraphSync)

---

## CGS-BETA, CGS-ALPHA and GX4G

`@CGS` is **CGS-BETA**: the Living Graph Python package, built by coupling
two components.

| Component | Role | Source |
| --- | --- | --- |
| **CGS-ALPHA** | [ComplexGitSync](https://github.com/flipoyo/ComplexGitSync): a distributed, git-native Operating Space. A project is a **GitTree**, a tree of nested Git repositories synchronised, versioned and restored as one unit, with a hash-chained memory of every State it goes through. | `github.com:flipoyo/ComplexGitSync` |
| **GX4G** | The **GATE** between `G` and `X`: it manages the state transitions of `G` requested by `X`. | `codeberg.org:gx4g/gx4g` |
| **CGS-BETA** | GX4G coupled with CGS-ALPHA: the Living Graph Python package. | this repository (`@CGS`) |

```text
CGS-BETA := GX4G + CGS-ALPHA
```

CGS-ALPHA supplies persistence and reproducibility: every State is recorded
and can be rebuilt exactly on another machine. GX4G supplies control: `X`
never changes `G` directly, it requests a transition and the gate manages it.
CGS-BETA lifts both into a graph: the living graph is what gets seeded,
persisted and retrieved.

```text
X  --request-->  GX4G  --transition-->  G
```

### The Living Graph package

The package is the living graph `G`, composed of four parts:

```text
NAME = G{ NAME, NODE, EDGE, OP }
```

It is the living instance of the PRIME graph, whose primitives are:

```text
G := { NAME-G, NODE-G, EDGE-G, OP }
```

| Part | Meaning |
| --- | --- |
| `NAME` | the name of the graph, which makes it addressable |
| `NODE` | the nodes of the graph (PRIME `NODE-G`) |
| `EDGE` | the edges between nodes (PRIME `EDGE-G`) |
| `OP` | the operations that act on the graph (PRIME `OP`) |

PRIME defines the primitives; the living package instantiates them:

```text
PRIME  G  := { NAME-G, NODE-G, EDGE-G, OP }
LIVING @G := G{ NAME, NODE, EDGE, OP }
```

The formal definition lives in the GitRepo [ComplexGraphSync](codeberg.org/gx4g/ComplexGraphSync).


---

## What @CGS Is For

`@CGS` is the Universal and Unique entry point to Living Graphs denoted *G. 

Use `@CGS` to turn an input into a living graph that can be seeded, interpreted as graph state and graph space, persisted, and later retrieved.

In practical terms, `@CGS` is for:

- booting a public ontological NODE-G state-space entry-point 
- booting a private  NODE-G space-state corresponding to OP-G
- adapting input deterministically without mutating the input EDGE-G GX4G-OP
- resolving input into a living graph instance through EDGE-G GX4G-NODE
- reading the graph as deterministic state or contextual space .cgs
- making the result addressable .gts

The README answers what to use `@CGS` for. The ontology answers what `@CGS` is.

---

## The OP Frontier

The class `OP` of ComplexGitSync is the **Graph Frontier** between CGS-ALPHA
and CGS-BETA. Every `cgitsync` operation (`bootstrap`, `pull`, `checkout`,
`commit`, `push`, `merge`, `tag`, `memory`, `omniscience`) is an `OP` of `G`.
Nothing crosses from one side to the other except through `OP`.

```text
CGS-BETA   X --request--> GX4G --OP--> G (living graph)
                                       |
 ----------------------- OP frontier --+------------------------
                                       |
CGS-ALPHA                              v
           GitTree --OP--> new State (.gts) --> memory --> omniscience
```

| Side | Holds | Artifact |
| --- | --- | --- |
| CGS-BETA | the living graph `G{NAME, NODE, EDGE, OP}`, gated by GX4G | `@G` |
| `OP` | the transition: what `X` requested and GX4G accepted | `cgitsync` command |
| CGS-ALPHA | the GitTree, its recorded States and its memory | `.cgs`, `.gts` |

- `.cgs` describes the topology of a graph's GitTree (the repositories it is made of).
- `.gts` records one State: the exact commit of every repository.
- The memory logs each State and the `OP` that produced it, in a verifiable hash chain.

---

## Entry Points

`@CGS` boots a living graph. The input is never mutated.

```text
@CGS(.)         public boot, from the canonical public seed
@CGS(., Α)      private boot, carrying the imprint Α
@HI := @CGS($HI, $HI.PRIVATE@)    adapt a received input $HI into @HI
```

`@HI` is the living graph derived from `$HI`; `$HI` stays as received.
To derive an instance through several imprints:

```text
.Χ := @CGS(.)
for i in <list>
    .Χ := @CGS(.Χ, i)
return .Χ
```

---

## Usage Map

| Need | Use | Result |
| --- | --- | --- |
| Public graph | `@CGS(.)` | `.Χ` from the public seed |
| Private graph | `@CGS(., Α)` | `.Χ` imprinted by `Α` |
| Adapt an input | `@CGS($HI, $HI.PRIVATE@)` | `@HI` |
| Change the graph | `X` requests, GX4G gates | an `OP` and a new State |
| Materialise a graph | `cgitsync bootstrap <graph>.cgs` | the GitTree on disk |
| Persist a State | `cgitsync add · commit · push · tag` | `.gts` snapshot and memory entry |
| Restore a State | `cgitsync bootstrap <state>.gts` | the exact recorded GitTree |
| Register and prove | `cgitsync omniscience register · verify` | a State readable from anywhere |

---

## Typical Flow

1. Receive the input `$HI`, or start from the public seed.
2. Call `@CGS` to obtain the living graph `@HI`.
3. `X` requests a change of `G`; GX4G gates it.
4. The accepted request crosses the `OP` frontier as a `cgitsync` operation.
5. CGS-ALPHA records the new State (`.gts`) in the memory.
6. Retrieve any recorded State later, here or on another machine.

---

AUTH: Nicolas Flipo

License: Apache-2.0

@ := 2026-10-29

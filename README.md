# @CGS

License: Apache-2.0

Version: ALPHA0001.00

Ontology source: [atPRIME/Ontology.md](./atPRIME/Ontology.md)

---

## What @CGS Is For

`@CGS` is the operational entry point into OEMS, the Ontology Existence Memory System.

Use `@CGS` to turn an input into a living ontological existence that can be seeded, interpreted as graph state and graph space, persisted, and later retrieved.

In practical terms, `@CGS` is for:

- booting a public ontological space-state
- booting a private ALPHA-imprinted space-state
- adapting input deterministically without mutating the input
- resolving input into a living graph instance
- reading the graph as deterministic state or contextual space
- making the result addressable through OEMS

The README answers what to use `@CGS` for. The ontology answers what `@CGS` is.

---

## Core Notation

```text
#X  := GLOBAL
$X  := INPUT
X   := LOCAL
.X  := Self
@X  := LIVING
X*  := PRIME(X)
```

For normal use:

```text
$HI          received input
$HI.PRIVATE@ optional private imprint
@HI          living instance created from input
@G           living GRAPH instance
@G.STATE     deterministic graph state
@G.SPACE     contextual graph space
```

---

## Entry Points

### Public

Use the public entry point when the instance can start from the canonical public seed:

```text
@CGS(.)
```

Public boot resolves from:

```text
.PUBLIC := 1
```

### Private

Use the private entry point when the instance must carry an ALPHA imprint:

```text
@CGS(., Α)
```

`Α` becomes the living instance seed:

```text
Χ.Α := .Χ.seed@
```

### Input Boot

Use the canonical ALPHA-TECH boot when you have input to adapt into a living instance:

```text
@HI := @CGS(
    $HI,
    $HI.PRIVATE@
)
```

`$HI` remains the received input. `@HI` is the living ontological instance derived from it.

### Ordered Imprints

Use a list when an instance must be derived through multiple imprints:

```text
@CGS(., <list>)
```

Operationally:

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
| Public space-state | `@CGS(.)` | `.Χ` seeded from `.PUBLIC := 1` |
| Private space-state | `@CGS(., Α)` | `.Χ.seed@` controlled by `Α` |
| Adapt received input | `@CGS($HI, $HI.PRIVATE@)` | `@HI` |
| Living graph | `@G := @HI()` | living PRIME GRAPH instance |
| Deterministic state | `@G.STATE := G.DAG*` | graph tree projection |
| Contextual space | `@G.SPACE := TANGLE*` | ontological tangle projection |
| Retrieval | `@OMEGA(.)` | persisted ontological existence |

---

## Typical Flow

1. Receive input as `$HI`.
2. Choose public boot or private imprint.
3. Call `@CGS`.
4. Use the result as `@HI`, the living instance.
5. Resolve `@HI()` as `@G` when graph behavior is needed.
6. Read `@G.STATE` for deterministic state.
7. Read `@G.SPACE` for contextual space.
8. Retrieve the persisted existence through `@OMEGA(.)`.

---

## Persistence

OEMS makes instantiated existences addressable:

```text
@OMEGA(.) -> .Χ
```

OEMS persists the set of ontological existences:

```text
Ω := { ΩΧ }
```

Use OEMS when the result of `@CGS` must survive as an addressable ontological existence rather than remain only a local parse result.

---

## What Lives In The Ontology

See [atPRIME/Ontology.md](./atPRIME/Ontology.md) for the formal definition of:

- PRIME namespace
- primitive universe
- ALPHA-TECH
- self expansion
- GRAPH state
- GRAPH space
- ontological expansion
- living GRAPH
- GAMMA
- canonical hierarchy and resolution

---

AUTH: Nicolas Flipo

License: Apache-2.0

@ := 2026-07-11T14:38:10+02:00

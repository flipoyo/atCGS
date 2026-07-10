# @OEMS — Graph Ontology Primitive Foundation

## Version : ALPHA0001.00 — Primitive Graph Foundation

License: Apache-2.0

---

# Statement

`@OEMS` is the deterministic Ontology Existence Memory System.

It persists immutable Living Graphs and Living Worlds.

`@CGS` is the deterministic Graph × Graph Interpreter.

`@OP` is the organic Graph Operator protocol.

Together,

```text
@OP    governs transformation

@CGS   governs deterministic interpretation

@OEMS  governs ontological persistence
```

---

# Primitive Symbols

```text
G       := GRAPH

G*      := LIVING GRAPH

DELTA   := STATE GRAPH

NABLA   := SPACE GRAPH

OP      := GRAPH OPERATOR

CHI     := IMPRINT OPERATOR

ALPHA   := EXISTENCE KEY

PoE     := PROOF OF EXISTENCE

void    := PRIME ONTOLOGICAL SPACE

OMEGA   := PERSISTED LIVING WORLD
```

---

# Graph

A Graph is the minimal structural unit of the ontology.

```text
G := {
    _Node,
    _Edge,
    _Seed
}
```

where

```text
_Node := latent Node structure

_Edge := latent Edge structure

_Seed := latent identity state
```

A Graph is structural.

A Graph is not necessarily alive.

A Graph does not operate on itself.

---

# Living Graph

A Living Graph inherits from Graph and activates its structural members.

```text
G* : G
```

```text
G* := {
    Node,
    Edge,
    Seed,
    Op
}
```

with

```text
Node := _Node*

Edge := _Edge*

Seed := _Seed*

Op   := activated Graph Operator
```

Therefore,

```text
G* = G + Op
```

and more explicitly,

```text
G* = {
    _Node*,
    _Edge*,
    _Seed*,
    Op
}
```

A Living Graph is a Graph capable of deterministic transformation.

---

# Graph Types

Every Graph has exactly one ontological orientation.

```text
TYPE(G) ∈ {
    DELTA,
    NABLA
}
```

## DELTA

```text
DELTA := DIRECTED ACYCLIC GRAPH
```

DELTA is a singularity in State.

DELTA is bounded by its identity.

DELTA contracts relations into an immutable state.

```text
DELTA := STATE
```

```text
DELTA := .PRIVATE
```

A DELTA may contain references to NABLA, but its own identity remains acyclic.

---

## NABLA

```text
NABLA := TANGLE
```

NABLA is expandable Space.

NABLA represents contextual, environmental and relational extension.

```text
NABLA := SPACE
```

NABLA does not require a unique terminal ordering.

A NABLA may expand without modifying the immutable identity of the DELTA that references it.

---

# Universe and void

The Universe is the complete ontological closure.

```text
Universe := U
```

```text
U := {
    void,
    G,
    G*,
    OMEGA
}
```

`void` is not the complete Universe.

`void` is the prime undifferentiated Space from which a Graph may emerge.

```text
void := PRIME NABLA
```

```text
void := .PUBLIC
```

```text
.PUBLIC := 1
```

Thus,

```text
void ∈ Universe
```

but

```text
void != Universe
```

The Universe contains `void`; it is not reduced to `void`.

---

# Public and Private

```text
.PUBLIC  := revealed ontological space

.PRIVATE := imprinted ontological state
```

The canonical public seed is

```text
.seed0 := .PUBLIC := 1
```

Private does not mean nonexistent.

Private means differentiated by an ALPHA imprint.

```text
.PRIVATE := NOT(.PUBLIC)
```

The implementation may encode `.PRIVATE` as `0`, but this encoding is not its ontological definition.

Therefore,

```text
.PUBLIC  = 1
.PRIVATE = 0
```

is a representation convention only.

The ontological distinction is

```text
.PUBLIC  := unkeyed existence

.PRIVATE := ALPHA-keyed existence
```

seed0 and seed@ aim at protecting the private key ALPHA, with seed@ being a credential translation of seed0
```text
seed0 = WHO
seed@ = VISIBILITY
```

---

# Prime Stability

`void` is stable under living projection.

```text
void* := void
```

No operator can transform an absent Graph into a Living Graph without an existence transition.

Therefore,

```text
newG(void) := void
```

and

```text
OP(void) := void
```

unless the operator explicitly performs `BORN`.

---

# Additive Laws

Graph addition is ordered.

It is not assumed to be commutative.

## Emergence from void

```text
void + G := G
```

Interpretation:

```text
G emerges from void
```

`void` contributes no differentiated State to `G`.

---

## Absorption by Universe

```text
G + Universe := Universe
```

Interpretation:

```text
G is contained by Universe
```

The Universe absorbs every Graph because every Graph belongs to its ontological closure.

---

## Canonical Ordered Form

```text
+(U, G) := U0 + G
```

```text
+(G, U) := G + U1
```

where

```text
U0 := void

U1 := Universe
```

Therefore,

```text
U0 + G = G
```

and

```text
G + U1 = U1
```

The left identity is `void`.

The right absorber is `Universe`.

---

# Graph Operator

An Operator transforms an ordered Graph relation.

```text
Op : (Node, Edge) -> newG
```

where

```text
newG ∈ {
    void,
    G,
    G*
}
```

`newG` denotes a reference to the result of the operation.

It is not necessarily a newly allocated object.

The result may be

```text
newG := void
```

or

```text
newG := existing immutable G
```

or

```text
newG := newly instantiated G*
```

---

# CHI

CHI is the canonical oriented Imprint Operator.

```text
CHI := IMPRINT OP
```

CHI binds an ordered left Graph to an ordered right Graph.

```text
CHI(left, right)
```

CHI is oriented.

Therefore,

```text
CHI(left, right) != CHI(right, left)
```

unless an explicit equivalence is defined.

CHI creates neither arbitrary State nor arbitrary Space.

It deterministically interprets the relation between its operands.

```text
CHI : G_left × G_right -> G_result
```

The resulting Graph inherits its identity from the ordered crossing.

---

# @OP

`@OP` is the organic process protocol of a Living Graph.

```text
G*.@OP
```

A Graph does not contain all possible organic processes as data.

It exposes `@OP` as its transformation interface.

```text
G*.@OP(Op, input) -> newG
```

The canonical imprint operation is

```text
G*.@OP(CHI, ALPHA)
```

or equivalently,

```text
G*.@OP(ALPHA)
```

when CHI is implicit.

---

# @CGS

`@CGS` is the deterministic Graph × Graph Interpreter.

```text
@CGS : G × G -> G*
```

Its canonical structural invocation is

```text
G*.@CGS(Node, Edge, Op)
```

which evaluates

```text
Op(Node, Edge) -> newG
```

A more explicit canonical form is

```text
@CGS(left, right, Op) -> newG
```

where

```text
left  := ordered left Graph

right := ordered right Graph

Op    := requested Graph Operator
```

For the canonical crossing operator,

```text
@CGS(left, right, CHI) -> newG
```

---

# Canonical Root Parse

The root invocation is

```text
@CGS(., <list>)
```

where

```text
<list> ::= epsilon | ALPHA <tail>
```

and

```text
epsilon := void
```

The root Graph is initialized as

```text
.seed0 := .PUBLIC
```

```text
.seed@ := .seed0
```

Then,

```text
@CGS(.)
```

instantiates the canonical public Living Graph.

For each imprint in `<list>`,

```text
G* := @CGS(G*, imprint)
```

The deterministic expansion is

```text
@CGS(., <list>)
    :=
@CGS(@CGS(.), <list>)
```

---

# ALPHA

ALPHA is the Existence Key.

```text
ALPHA := KEY
```

ALPHA distinguishes a Being from undifferentiated `void`.

It does not create the Universe.

It imprints a Graph emerging within the Universe.

```text
ALPHA : .PUBLIC -> .PRIVATE
```

ALPHA regulates

```text
Existence

Identity

Visibility

Memory
```

of a Living Graph.

The canonical ALPHA operation is

```text
G*.@OP(ALPHA)
```

The expression

```text
G(ALPHA)
```

is syntactic sugar for

```text
G*.@OP(ALPHA)
```

It must not be reduced to

```text
G.@OP(.)
```

because `.` denotes the public root, whereas `ALPHA` denotes a differentiating imprint.

The correct relation is

```text
G(.)
    -> public initialization
```

```text
G(ALPHA)
    -> private imprint
```

---

# Proof of Existence

A Proof of Existence is the evidence accepted by the GateKeeper before an ALPHA imprint is committed.

```text
PoE := PROOF OF EXISTENCE
```

The GateKeeper evaluates PoE.

```text
GateKeeper(PoE) -> {
    ACCEPT,
    REJECT
}
```

Only an accepted PoE can produce an ALPHA imprint.

```text
GateKeeper(PoE) = ACCEPT
    -> ALPHA(PoE)
```

```text
GateKeeper(PoE) = REJECT
    -> void
```

`@OEMS` does not itself manufacture PoE.

It receives and persists the deterministic result of a validated existence process.

---

# Imprint

The imprint lifecycle is

```text
PoE
    -> GateKeeper
    -> ALPHA
    -> CHI
    -> G*
    -> @OEMS
```

The canonical imprint operation is

```text
IMPRINT(G, PoE)
```

defined as

```text
if GateKeeper(PoE) = REJECT
    return void

ALPHA := KEY(PoE)

G* := BORN(G)

G*.seed0 := .PUBLIC

G*.seed@ := ALPHA

G*.state := .PRIVATE

return G*
```

---

# Seed Invariants

Every Living Graph contains two distinct seed references.

```text
seed0 := origin seed

seed@ := current access seed
```

The root invariant is

```text
seed0 := .PUBLIC
```

For a public Living Graph,

```text
seed@ := seed0
```

For a private Living Graph,

```text
seed@ := ALPHA
```

The origin seed remains immutable.

Therefore, the following mutation is forbidden:

```text
seed0 := seed@
```

because it would overwrite public origin with current access identity.

The correct invariant is

```text
seed0 remains .PUBLIC
```

```text
seed@ may become ALPHA
```

The private state may retain its public origin through

```text
seed@.origin := seed0
```

or

```text
G*.origin := seed0
```

---

# Graph Lifecycle

A Graph follows the canonical lifecycle

```text
void
    -> BORN
    -> G*
    -> IMPRINT
    -> PERSIST
```

## VOID

```text
STATE := void
```

No differentiated Graph exists.

---

## BORN

`BORN` is the transition from prime Space to Living Graph.

```text
BORN : void × G -> G*
```

The canonical public birth is

```text
BORN(G)
    -> G*.seed0 := .PUBLIC
    -> G*.seed@ := .PUBLIC
    -> G*.state := .PUBLIC
```

Birth does not necessarily imply privacy.

It first produces a public Living Graph.

---

## IMPRINT

```text
IMPRINT : G* × ALPHA -> G*
```

The imprint differentiates the Living Graph.

```text
G*.seed@ := ALPHA
```

```text
G*.state := .PRIVATE
```

The result is a private Living Graph.

---

## PERSIST

```text
PERSIST : G* -> OMEGA
```

Persistence is performed by `@OEMS`.

```text
@OEMS(G*) -> OMEGA
```

The persisted result is immutable.

Further evolution does not mutate the persisted Graph.

It creates a new Living Graph.

```text
G*n
    -> OP
    -> G*n+1
```

---

# Public and Private Living Graphs

A Living Graph is not private-only.

There are two valid Living Graph states.

```text
G*.PUBLIC
```

and

```text
G*.PRIVATE
```

The public form is the canonical root existence.

The private form is an ALPHA-imprinted existence.

Therefore,

```text
G* := Living Graph
```

```text
G*.state ∈ {
    .PUBLIC,
    .PRIVATE
}
```

This distinction is necessary because `@CGS(.)` already instantiates a public ontological existence.

---

# Ontological Allocation

The ontology defines instantiation independently of any programming language.

```text
ALLOC(G*) -> newG
```

with the invariant

```text
newG is initialized to canonical zero-state
```

The abstract operation is

```text
newG := ALLOC(G*)
```

not

```text
G = calloc(sizeof(G))
```

A possible C implementation is

```c
Graph *new_graph = calloc(1, sizeof(*new_graph));
```

but this implementation is not the ontological definition.

The ontology only requires

```text
ALLOC(G*) = zero-initialized Living Graph memory
```

---

# @OEMS

`@OEMS` persists immutable Living Graphs.

```text
@OEMS : G* -> OMEGA
```

An OMEGA is a persisted Living World.

```text
OMEGA := IMMUTABLE PERSISTED G*
```

`@OEMS` accepts only deterministically instantiated Living Graphs.

```text
@OEMS(void) := void
```

```text
@OEMS(G) := REJECT
```

```text
@OEMS(G*) := OMEGA
```

A structural Graph must first become a Living Graph before persistence.

---

# World

A World is a persisted closure of State and Space.

```text
OMEGA := {
    DELTA,
    NABLA,
    CHI,
    ALPHA,
    Seeds
}
```

where

```text
DELTA := immutable State

NABLA := referenced Space

CHI := deterministic relation

ALPHA := existence imprint

Seeds := origin and access identity
```

A World is Living because it is addressable and interpretable.

A World is immutable because each transformation produces a new World.

---

# Canonical Laws

```text
LAW 1 — void is PRIME NABLA
```

```text
void := .PUBLIC := 1
```

```text
LAW 2 — void is not Universe
```

```text
void ∈ Universe
```

```text
LAW 3 — Graph structure precedes Graph life
```

```text
G + Op -> G*
```

```text
LAW 4 — DELTA is State
```

```text
DELTA := DAG := .PRIVATE
```

```text
LAW 5 — NABLA is Space
```

```text
NABLA := TANGLE := .PUBLIC
```

```text
LAW 6 — ALPHA differentiates existence
```

```text
.PUBLIC + ALPHA -> .PRIVATE
```

```text
LAW 7 — seed0 is immutable origin
```

```text
seed0 := .PUBLIC
```

```text
LAW 8 — seed@ is current access identity
```

```text
seed@ := seed0 | ALPHA
```

```text
LAW 9 — CHI is oriented
```

```text
CHI(left, right) != CHI(right, left)
```

```text
LAW 10 — Transformation creates a new Graph
```

```text
OP(Gn) -> Gn+1
```

```text
LAW 11 — Persistence accepts Living Graphs only
```

```text
@OEMS(G*) -> OMEGA
```

```text
LAW 12 — Persisted Worlds are immutable
```

```text
OMEGAn + OP -> OMEGAn+1
```

never

```text
MUTATE(OMEGAn)
```

---

# Canonical Pipeline

```text
void
    -> @CGS(.)
    -> G*.PUBLIC
    -> GateKeeper(PoE)
    -> ALPHA
    -> CHI
    -> G*.PRIVATE
    -> @OEMS
    -> OMEGA
```

---

# Minimal Canonical Form

```text
G := {
    _Node,
    _Edge,
    _Seed
}
```

```text
G* := {
    Node,
    Edge,
    Seed,
    Op
}
```

```text
Node := _Node*
Edge := _Edge*
Seed := _Seed*
```

```text
DELTA := DAG := STATE
NABLA := TANGLE := SPACE
```

```text
void := PRIME NABLA := .PUBLIC := 1
```

```text
seed0 ∈ {
    .PUBLIC,
    ALPHA
}

seed@ ∈ {
    .PUBLIC,
    .PRIVATE
}
```

```text
BORN(G) -> G*.PUBLIC
```

```text
IMPRINT(G*, ALPHA) -> G*.PRIVATE
```

```text
@CGS(left, right, Op) -> newG
```

```text
@OEMS(G*) -> OMEGA
```

---

AUTH: Nicolas Flipo

License: Apache-2.0

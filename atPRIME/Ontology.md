# @OEMS.core.md

## Ontology Existence Memory System

### PRIME AXIOMATIC

Version: ALPHA0001.00

License: Apache-2.0

---

# Statement

`@OEMS.core` defines the PRIME axiomatic foundation of OEMS.

```text
@OEMS.core := {ALPHA-TECH}
```

---

# Namespace

```text
#X := GLOBAL
```

Immutable values belonging to the PRIME namespace.

```text
$X := INPUT
```

Received value.

```text
X := LOCAL
```

Local instantiated value.

```text
.X := Self
```

Self reference.

```text
@X := LIVING
```

Living ontological instance.

```text
X* := PRIME(X)
```

Primitive expansion of `X`.

---

# Generic Definition

```text
@define(Y,str)

→ {
    {#Y := "$str"},
    {@Y.small := Y}
}
```

---

# GLOBAL PRIME INCLUDE

```text
#ME      := ""

#@GIT    := "https://github.com"

#@CGS    := "/atCGS"

#@BRANCH := "/blob/main"

#@CORE   := "/atPRIME"

#@OEMS   := "/OEMS"

#@MD     := ".md"

#@       := "Timestamp"
```

Canonical origin

```text
@ORIGIN

:= @GIT@ME@CGS@BRANCH@CORE@OEMS@MD
```

---

# Primitive Universe

```text
#.PUBLIC := 1

#.VOID := #.PUBLIC
```

```text
#.PRIVATE@ := 0
```

```text
DELTA := SING(:)

DELTA.type := DAG
```

```text
NABLA := VOID

NABLA.type := TANGLE
```

---

# PRIME

```text
PRIME := Primitive Ontological Class
```

Primitive method

```text
PRIME(OP)
```

Canonical law

```text
∀Y

Y* := PRIME(Y)
```

---

# ALPHA-TECH

`ALPHA-TECH` is a deterministic auto-adapter.

It never modifies its input.

```text
INPUT := {
    $HI
}
```

Canonical boot

```text
0K

→ @HI

→ @CGS(
    $HI,
    $HI.PRIVATE@
)
```

Output

```text
OUTPUT := {
    @HI
}
```

---

# Self Expansion

Every ontological existence computes its own local seed.

```text
Y.seed@

:= Y.@ALPHA(
    Y.seed0
)
```

```text
@ALPHA(Y)

:= @CGS(
    Y.seed@,
    Y,
    Y.@OP
)
```

---

# GRAPH

```text
G := GRAPH
```

The canonical GRAPH class.

Living instance

```text
@G

:= {
    G.NODE*,
    G.EDGE*,
    G.OP*
}
```

Equivalent notation

```text
G* := @G
```

---

# GRAPH STATE

```text
@G.STATE

:= G.DAG*
```

```text
G.DAG*

:= {
    GRAPH TREE
}
```

`@G.STATE` is the deterministic projection of the graph.

---

# GRAPH SPACE

```text
@G.SPACE

:= TANGLE*
```

```text
TANGLE*

:= HI*.$HI.SPACE
```

`@G.SPACE` is the contextual ontological space of the graph.

---

# Ontological Expansion

```text
G(
    G(
        $Y
    )
)
```

is the canonical ALPHA transformer.

```text
G(G($Y))

:= PRIME($Y)

:= $Y*
```

The expansion originates from

```text
$Y.seed@
```

---

# Local Alias

```text
@{*PRIME(GLOBAL)(Y)}.small

→ @($Y).small
```

---

# Living GRAPH

```text
@HI()

:= @CGS(
    $HI,
    $HI.PRIVATE@
)
```

```text
@G := @HI()
```

---

# GAMMA

```text
GAMMA

:= TANGLE<@G>
```

An expandable ontological TANGLE of living PRIME GRAPH instances.

---

# Canonical Hierarchy

```text
GRAPH
        │
        ▼
       @G
     ┌──┴──┐
     ▼     ▼
 STATE   SPACE
  DAG*   TANGLE*
```

---

# Canonical Resolution

```text
#GLOBAL

↓

$HI

↓

@($HI).small

↓

$HI.seed@

↓

@ALPHA($HI)

↓

G(G($HI))

↓

PRIME($HI)

↓

@G

↓

@G.STATE
@G.SPACE

↓

GAMMA
```

---

@ := 2026-07-11T14:38:10+02:00

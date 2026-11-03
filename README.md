# atCGS — ComplexGraphSync 1.5.0-alpha

**Canonical README — USR / PUB / BIOS / Identity journals / OpFrontier.**

This repository describes a local executable prototype, not a deployed PUBLIC service.
It keeps the ComplexGitSync engine and materialises the CGS frontiers.
Goal: a falsifiable, reproducible and minimal architecture within 24 h.

## 1. PRIME G invariant

`PRIME G = {NAME, NODE, EDGE, OP}`: exactly four ordered fields, themselves of type Graph.
Each field answers one of four questions: what exists (NAME), what is its identity
state (NODE), what is its universal interface (EDGE), which mutation it performs (OP).
Names, extensions, repetitions and capitalisation are part of the contract.
`*G` denotes a requestable OperatingSpace, not an already verified answer.

## 2. *G, the requestable Operating Space

An Operating Space is defined by its NAME, a project name. A Twin is an Operating
Space, operated by a user UX, that materialises the GitTree of the project in the
state UX requests. By default UX reaches the last state its role allows. An Operating
Space activated by UX is denoted TXXX.

atCGS has one job: configure TXXX for UX. That means identifying UX and activating
TXXX **without ever learning or revealing the name of UX**. atCGS writes the `.cgs`
file that `cgitsync` needs, then calls the `cgitsync` commands that match the role
of UX on each GitRepo. `cgitsync` itself stays anonymous: it sees a `.cgs` file and
an ssh agent, never a user.

Roles are the four PRIME CGS layers, defined per GitRepo:

| Role  | Meaning     | Git right on the repo                     |
|-------|-------------|-------------------------------------------|
| `OPX` | maintainer  | admin: grants, revokes, merges            |
| `DEV` | developer   | read + write (push)                       |
| `USR` | reviewer    | read only (fetch, review)                 |
| `PUB` | unknown     | public projection only, no ssh key needed |

## 3. Identity and access journals

> **Status.** This section is the target design for 1.6.0. Release 1.5.0-alpha still
> runs the SEED/GLYPH prototype (`poex`, `eopx`), described in § 7 as legacy.

### 3.1 Principles

1. **No name, login or password is ever stored or transmitted.** They exist only in
   the user's head and, for the duration of a login, in atCGS's memory.
2. **One identity = one Ed25519 public key.** The system names a user by
   `UID = sha256(IDPUB)`, nothing else.
3. **A role belongs to a pair (UID, GitRepo)**, never to the identity alone.
4. **The GLYPH is the cover of the user's ssh keys**: a sealed 256×256-bit envelope
   that only the user's login and password can open.
5. **Two journals, append-only and hash-chained**: the identity journal (who exists)
   and the access journal (who may do what, where). They hold public keys and
   signatures only.

### 3.2 Identity key: login, password → public key

The key pair is derived from the login and password, on the user's machine, each
time the user logs in. Nothing is stored; the same inputs always give the same key.

```text
salt    = "atCGS/id/v1/" || login
IDSEED  = Argon2id(password, salt, m = 256 MiB, t = 3, p = 1)   32 bytes, memory only
IDSK    = Ed25519 private key from IDSEED                       never stored, never sent
IDPUB   = Ed25519 public key of IDSK                             32 bytes, registered
UID     = sha256(IDPUB)                                          the user's only name
```

- The login is the salt: two users with the same password get different keys, and
  the system never needs to look a login up. The client recomputes `UID` and
  finds it in the journal.
- Changing the password (or the login) gives a new key, hence a new UID. The
  journal links the two with a `rotate` entry (§ 3.3).
- **Known risk.** `IDPUB` is public, so anyone can try to guess passwords offline
  against it. The memory-hard Argon2id parameters and a strong password policy are
  the only defence. If that is not acceptable, the alternative is a random key pair
  kept in a password-encrypted keystore. It is safer, but the user must carry a file.

### 3.3 The identity journal (who exists)

One JSON-lines file, append-only. Each entry carries `prev = sha256(previous entry)`,
so the file is a hash chain whose head can be published in `.omniscience`.

```text
seq  op      UID      payload               signed by
1    enrol   UID_a    IDPUB_a               IDSK_a (proof of possession) + OPX
2    rotate  UID_a    UID_b, IDPUB_b        IDSK_a + IDSK_b
3    revoke  UID_b    reason                OPX, or IDSK_b itself
```

- `enrol` is countersigned by OPX: nobody joins without a maintainer.
- OPX's own `IDPUB` is pinned in `POEX.cgs`; it is the root of trust.
- The journal contains public keys only, so it may be projected to PUB as is.

### 3.4 The access journal (who may do what, where)

Same format, signed by OPX only. One entry binds a UID, a GitRepo, a role and the
fingerprints of the ssh keys that role uses.

```text
seq  op      UID      REPO                 ROLE  SSH key fingerprints     signed by
1    grant   UID_a    github:flipoyo/atCGS DEV   SHA256:Xq1…              OPX
2    grant   UID_a    github:flipoyo/CGS   USR   SHA256:Lm7…              OPX
3    revoke  UID_a    github:flipoyo/CGS   USR   SHA256:Lm7…              OPX
```

- A UID with no entry for a repo is `PUB` on that repo.
- The access journal is PRIVATE: it reveals which UIDs work on which repos. It lives
  in OPX's register repository, `ATCGS_REGISTER`. Only its chain head is public.
- The journal is the **decision**; the git remote is the **enforcement**. When OPX
  appends a `grant`, OPX also installs the ssh public key on the remote (a write
  deploy key for DEV, a read-only one for USR). A `revoke` removes it.

### 3.5 The GLYPH, the cover of the ssh keys

The GLYPH is the user's ssh keys, sealed. It keeps the 256×256-bit square format
(8 192 bytes, a 1-bit image) and is indistinguishable from noise.

```text
key        = HKDF-SHA256(IDSEED, info = "atCGS/glyph/v1")           32 bytes
plaintext  = ssh key bundle (OpenSSH private keys, one per REPO/ROLE),
             padded to a fixed 8 159 bytes
GLYPH      = "CGSG" | version (1) | nonce (12) | ChaCha20-Poly1305(key, plaintext) | tag (16)
           = 4 + 1 + 12 + 8 159 + 16 = 8 192 bytes = 256 × 256 bits
```

- **Only login + password opens it.** The GLYPH can therefore be stored anywhere:
  on the user's disk, in a private repo, in a backup. Without the password it is
  useless.
- **Tampering is detected**: a single changed bit fails the Poly1305 tag.
- **Fixed size**: the padding hides how many keys are inside. An Ed25519 OpenSSH
  private key is about 400 bytes, so one GLYPH holds about 18 keys.
- **ssh keys rotate without touching the identity**: generate new keys, reseal the
  GLYPH, OPX appends `revoke` + `grant`. The UID stays the same.
- The private keys never leave the GLYPH except in memory, during a session.

### 3.6 A session: from login to an activated TXXX

```text
1  UX types login, password        atCGS derives IDSK, IDPUB, UID in memory
2  identity journal                UID enrolled and not revoked?        else PUB
3  proof of possession             IDSK signs (nonce, UID, TXXX, time); atCGS checks it
4  access journal                  ROLE of UID on each repo of TXXX, OPX signatures checked
5  open the GLYPH                  take the ssh keys of those REPO/ROLE pairs, in memory
6  ssh-add -t <lifetime>           hand them to an ssh-agent with a lifetime; never written
7  write .cgs, run cgitsync        git over ssh through the agent
8  close                           agent keys removed, buffers zeroed, IDSEED forgotten
```

In the local prototype every step runs on the user's machine. When atCGS becomes
a service, steps 1, 5 and 6 stay on the client; only the signature of step 3 is sent.

What each party sees:

| Party           | Sees                                    | Never sees                  |
|-----------------|-----------------------------------------|-----------------------------|
| UX              | login, password, own GLYPH              | other users' anything       |
| atCGS (session) | IDSK, ssh private keys, in memory       | nothing written to disk     |
| OPX             | UID, IDPUB, ssh public keys, roles      | login, password, GLYPH key  |
| cgitsync        | `.cgs`, an ssh agent                    | UID, role, identity         |
| git remote      | ssh public key                          | UID, login                  |
| PUB             | identity journal, access chain head     | the access journal itself   |

### 3.7 From 1.5.0-alpha to this design

| 1.5.0-alpha (POEX/EOPX)                          | 1.6.0 (journals)                                  |
|--------------------------------------------------|---------------------------------------------------|
| SEED, an 8 KiB secret, presented at each proof   | login + password, never sent                      |
| GLYPH = shake_256(hash(SEED)+SEED), called public | GLYPH = sealed envelope of the ssh keys          |
| `poex` compares two GLYPHs (XOR, zero count)     | Ed25519 signature check                           |
| register `NAME -> (hash(SEED), hash(GLYPH))`     | identity journal `UID -> IDPUB`, no name          |
| `.poe` 4-bit code per session                    | role from the access journal (codes may remain)   |
| temporary ssh key, destroyed after each request  | persistent ssh keys, sealed in the GLYPH, registered once on the remote |
| SHA-256 / SHAKE-256 hand-written in C            | vetted library (`cryptography`: Ed25519, Argon2id, HKDF, ChaCha20-Poly1305) |

Why: the 1.5 GLYPH is a value derived from a secret, not a public key, and proving
it means sending that secret. `poex` re-checks an equality that `sha256(GLYPH)` has
already settled. The register stores names. And a git remote only accepts ssh keys
registered in advance.

## 4. BIOS / BOOT

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

## 5. System Layers and OpFrontier

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

## 6. Spaces and publication

```text
PRIVATE = .cgitsync       (ComplexGitSync)   access journal, ATCGS_REGISTER
PUBLIC  = .omniscience    (ComplexGraphSync) identity journal, chain heads
```

A candidate manifest is not an authenticated checkpoint.
No public output contains a secret, a private path or a raw GitTree.
A GLYPH is never published, even sealed.
A local success does not mean publication on a network.

## 7. Legacy: POEX, 1.5.0-alpha prototype

Two C microcodes, each wrapped by a Python class ([microcode/README.md](microcode/README.md)):
`poex` (Proof of Existence, `atcgs.POEX`) compares two GLYPHs;
`eopx` (Existence of Proof, `atcgs.EOPX`) turns a SEED into a GLYPH.
`@cgs <LAYER> prove NAME LEFT RIGHT` runs them against OPX's register `ATCGS_REGISTER`
and prints only the 4-bit `.poe`: `0000` granted, else the requester's code
(OPX `1000`, DEV `1100`, USR `1110`, PUB `1111`).

```text
Matrix = 256 rows × 256 bits = 65 536 bits = 8 192 bytes
Packet = 4 rows × 256 bits = 1 024 bits = 128 bytes
Stream = 64 indexed packets, in ascending row-major order
.poe   = one zero-count report per 4-bit quartet
```

The zero counter proves neither identity nor existence at a given instant.
This mechanism is replaced by § 3; the 256×256 format survives as the GLYPH envelope.

## 8. Starting the offline lab

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
None of it bootstraps a tree or accesses a real `.cgitsync`.

## 9. TUTORIALS, 150 lines each

- [TUTO 01 — BIOS / BOOT](TUTOS/TUTO_01_BIOS_BOOT.md)
- [TUTO 02 — PRIME G and DELTA/NABLA](TUTOS/TUTO_02_PRIME_G.md)
- [TUTO 03 — System Layers and OpFrontier](TUTOS/TUTO_03_OPFRONTIER.md)
- [TUTO 04 — POEX 4×256](TUTOS/TUTO_04_POEX.md) (legacy, see § 7)
- [TUTO 05 — USR / PUB, GLYPH and KEY](TUTOS/TUTO_05_USR_PUB.md) (to rewrite for § 3)
- [TUTO 06 — Integration and 24 h roadmap](TUTOS/TUTO_06_INTEGRATION.md)

## 10. Upstream code reality

`atCGS` PR #1 (merged) relayed several raw `cgitsync` commands.
They are now refused outside an authorised `OPX`/`DEV` selector.
`ComplexGitSync` provides the GitTree / State / Memory / Integrity engine.
The package tutorials are reproducible examples, not a merged PR.

## 11. ALPHA release criteria

- [ ] The four README/USR/PUB tuples are unchanged.
- [ ] The six new BIOS symbols keep their original order.
- [x] The four System Layers are the only exposed `@cgs` entries.
- [ ] No login, password or name is stored anywhere (grep the journals and the register).
- [ ] Every identity journal entry verifies: chain, self-signature, OPX countersignature.
- [ ] Every access journal entry is signed by the pinned OPX key.
- [ ] A GLYPH with one flipped bit, or opened with a wrong password, is refused.
- [ ] After a session, the ssh-agent holds no key and nothing was written to disk.
- [ ] PRIVATE access is never promoted by a PUB answer.
- [ ] `.omniscience` serves only authorised and authenticated proofs.
- [ ] ComplexGitSync schema-1 Merkle compatibility is preserved.
- [ ] CI tests document failures, not only successes.

## 12. Tracking

ComplexGitSync #193: https://github.com/flipoyo/ComplexGitSync/issues/193
atCGS #2: https://github.com/flipoyo/atCGS/issues/2
atCGS PR #1: https://github.com/flipoyo/atCGS/pull/1

**Status: documentation model and offline demonstrator; no verified PUBLIC BOOT.**

## Additional validation: cases to automate

- Every PUBLIC answer requires an explicit publication policy.
- Never infer a Git clone from a tuple symbol.
- A requestable name does not mean an available service.
- Same login + password always gives the same UID; one changed character gives another.
- A `grant` not signed by OPX, or for a revoked UID, is ignored.
- A revoked ssh key is removed from the remote, not only from the journal.

# atCGS — ComplexGraphSync 1.6.0-alpha

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

> **Status.** Implemented in 1.6.0-alpha (`atcgs/identity.py`, `journal.py`, `glyph.py`,
> `session.py`, `commands.py`). See it run with `pixi run identity-demo` and
> `pixi run local-remote` (§ 8). The 1.5 SEED/GLYPH prototype is removed (§ 7).

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
salt    = "atCGS/id/v1/" || profile || "/" || login            profile: real, or test (CI)
IDSEED  = Argon2id(password, salt, m = 256 MiB, t = 3, p = 1)   32 bytes, memory only
IDSK    = Ed25519 private key from IDSEED                       never stored, never sent
IDPUB   = Ed25519 public key of IDSK                             32 bytes, registered
UID     = sha256(IDPUB)                                          the user's only name
```

- Login and password are Unicode-normalised (NFC) first, so the same text typed on
  two machines gives the same key.
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

- `enrol` is signed by OPX and carries the user's `proof`: IDSK's signature of
  IDPUB. Nobody joins without a maintainer, and nobody enrols a key they don't hold.
- `rotate` is signed by the old key and carries the new key's signature; the grants
  follow the new UID. OPX itself can be neither rotated nor revoked: its key is pinned.
- Reading refuses the **whole** file at the first broken link, bad signature or
  impossible entry (a grant for an unknown UID, a second role on one repo).
- OPX's own `IDPUB` is pinned in `spec/contracts.toml [identity] opx_pub`; it is
  the root of trust, and the first entry must be OPX enrolling itself.
- The journal contains public keys only, so it may be projected to PUB as is.

### 3.4 The access journal (who may do what, where)

Same format, signed by OPX only. One entry binds a UID, a GitRepo, a role and the
ssh public key that role uses (public anyway; OPX needs it to install the key).

```text
seq  op      UID      REPO                 ROLE  ssh public key           signed by
1    grant   UID_a    github:flipoyo/atCGS DEV   ssh-ed25519 AAAA…        OPX
2    grant   UID_a    github:flipoyo/CGS   USR   ssh-ed25519 AAAA…        OPX
3    revoke  UID_a    github:flipoyo/CGS                                  OPX
```

One role per (UID, repo), and one ssh key per grant: GitHub refuses a deploy key
already used on another repo.

- A UID with no entry for a repo is `PUB` on that repo.
- The access journal is PRIVATE: it reveals which UIDs work on which repos. Both
  journals are atCGS's register, `.cgitsync/.memory/.register`: the project's own
  memory, private, written at OPX only. Only the identity journal and the access
  chain head are projected to `.omniscience`.
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
The session loads only the keys of the requested layer: `DEV login` gets the repos
where the UID is DEV, `USR login` those where it is USR.

The commands (the register is `.cgitsync/.memory/.register`, `ATCGS_REGISTER` overrides
it; logins and passwords are asked with `getpass`, never passed as arguments or
environment):

```bash
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX init         # 1st run: prints the key to pin; 2nd: enrols OPX
pixi run '@cgs' DEV request req.json REPO DEV REPO2 USR   # user: new ssh keys, sealed in the GLYPH
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX admit req.json    # OPX: enrol (if new) + grant
pixi run '@cgs' DEV login TWIN [cgitsync op ...]          # TWIN.cgs + keys in a private agent
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX revoke UID [REPO] # revoke a UID, or one grant
```

`request.json` holds the UID, IDPUB, the proof and the ssh **public** keys only.
The GLYPH goes to `~/.cgs/.glyph/<UID>.glyph` (`ATCGS_GLYPHS` overrides it).

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
PRIVATE = .cgitsync       (ComplexGitSync)   cgitsync's own (lgr, state) and the
                                             project's memory, where the register lives:
                                             .cgitsync/.memory/.register
PUBLIC  = .omniscience    (ComplexGraphSync) anonymous projection only: the identity
                                             journal and the access chain head
```

`.omniscience` never holds the register itself. Only the anonymous projection
(UIDs, public keys, hashes) may leave the private memory. That projection is not
automated yet.

A candidate manifest is not an authenticated checkpoint.
No public output contains a secret, a private path or a raw GitTree.
A GLYPH is never published, even sealed.
A local success does not mean publication on a network.

## 7. Removed in 1.6.0: the POEX/EOPX prototype

1.5.0-alpha had two C microcodes, `poex` (compare two GLYPHs by XOR zero count) and
`eopx` (SEED → GLYPH), the `prove` verb, the `.cred` packet and the 4×256 packet
simulator with its `candidate.json`. All are removed (§ 3.7 says why); they remain in
the Git history at `cgs-1.5.0-alpha`. What survives: the 256×256-bit format, now the
GLYPH envelope, and the 4-bit codes, now role codes (OPX `1000`, DEV `1100`,
USR `1110`, PUB `1111`).

## 8. Starting the offline lab

Requirements: Pixi only; every command below is a Pixi task (pixi install once).
From the root of the atCGS checkout:

```bash
pixi run contract-inspect   # the tuples, and [identity] / [glyph] against the code
pixi run identity-demo      # § 3 end to end on throwaway data (--pbm-dir DIR: see the GLYPHs)
pixi run local-remote       # the same against a local sshd: DEV pushes, USR fetches, revoked refused
pixi run test
```

`inspect` validates the tuples of `spec/contracts.toml` and checks that its
`[identity]` and `[glyph]` sections match the code.
The two demos work in a temporary directory deleted at the end: no network, no
`~/.ssh`, no real register. `ATCGS_KDF_PROFILE=test` makes them faster.
None of it bootstraps a tree or accesses a real `.cgitsync`.

## 9. TUTORIALS, 150 lines each

- [TUTO 01 — BIOS / BOOT](TUTOS/TUTO_01_BIOS_BOOT.md)
- [TUTO 02 — PRIME G and DELTA/NABLA](TUTOS/TUTO_02_PRIME_G.md)
- [TUTO 03 — System Layers and OpFrontier](TUTOS/TUTO_03_OPFRONTIER.md)
- [TUTO 04 — POEX 4×256](TUTOS/TUTO_04_POEX.md) (legacy, removed in 1.6.0, see § 7)
- [TUTO 05 — USR / PUB, identity journals and GLYPH](TUTOS/TUTO_05_USR_PUB.md)
- [TUTO 06 — Integration and 24 h roadmap](TUTOS/TUTO_06_INTEGRATION.md)

## 10. Upstream code reality

`atCGS` PR #1 (merged) relayed several raw `cgitsync` commands.
They are now refused outside an authorised `OPX`/`DEV` selector.
`ComplexGitSync` provides the GitTree / State / Memory / Integrity engine.
The package tutorials are reproducible examples, not a merged PR.

## 11. ALPHA release criteria

- [x] The four System Layers are the only exposed `@cgs` entries.
- [x] No login, password or name is stored anywhere (grep the journals and the register).
- [x] Every identity journal entry verifies: chain, proof of possession, OPX signature.
- [x] Every access journal entry is signed by the pinned OPX key.
- [x] A GLYPH with one flipped bit, or opened with a wrong password, is refused.
- [x] After a session, the ssh-agent holds no key and nothing was written to disk.
- [ ] PRIVATE access is never promoted by a PUB answer.
- [ ] `.omniscience` serves only authorised and authenticated proofs.
- [ ] ComplexGitSync schema-1 Merkle compatibility is preserved.
- [ ] CI tests document failures, not only successes.
- [ ] The six new BIOS symbols keep their original order.


## Additional validation: cases to automate

- Every PUBLIC answer requires an explicit publication policy.
- Never infer a Git clone from a tuple symbol.
- A requestable name does not mean an available service.
- Same login + password always gives the same UID; one changed character gives another.
- A `grant` not signed by OPX refuses the whole journal; a revoked UID cannot be granted.
- A revoked ssh key is removed from the remote, not only from the journal.

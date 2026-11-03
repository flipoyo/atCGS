# TUTO 05 — USR / PUB, identity journals and GLYPH

**Status: current (1.7.1-alpha).** Every command below runs; each is covered by a test or by `identity-demo` / `local-remote`.

**Goal:** keep the four publication tuples intact, then identify a user and open
their ssh keys without ever storing a name or a password (README § 3).

## 1. New canonical frontier

```text
README atCGS USR PUB
DELTA POEX OPX HASH
HASH DELTA CGS OPX
.cgs USR PUB .toml
```

These are four `NAME NODE EDGE OP` records; the GLYPH row is gone.
`.wth` no longer exists; no tuple may reintroduce it.

## 2. Link with the earlier transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

The new table and the OpFrontier table serve distinct purposes.
Do not merge their fields to build five-column tuples.
Do not create an artificial fourth OpFrontier transition.

## 3. Watch it work first

```bash
pixi run identity-demo --pbm-dir /tmp/glyphs
```

It builds OPX, alice (DEV) and bob (USR) in a temporary directory and prints
each step, ending with four refusals. Open `/tmp/glyphs/alice.pbm`: it is noise.

```bash
pixi run local-remote
```

The same against a real `sshd` on localhost: alice pushes, bob only fetches,
and bob's key is refused as soon as OPX revokes it, even while it is loaded.

## 4. Identity: login, password → public key

```text
IDSEED = Argon2id(password, "atCGS/id/v1/" + profile + "/" + login)   memory only
IDPUB  = Ed25519 public key of IDSEED                                 registered
UID    = sha256(IDPUB)                                                the only name
```

The same login and password always give the same UID; one changed character
gives another. Nothing is looked up by login: the client recomputes the UID.
The cost is real: anyone holding IDPUB can try passwords offline, so the
Argon2id cost (256 MiB, 3 passes) and a long passphrase are the defence.

## 5. The two journals

```text
identity.jsonl   enrol | rotate | revoke    who exists       signed by OPX (enrol)
access.jsonl     grant | revoke             who may do what  signed by OPX only
```

Each line carries `prev = sha256(previous line)` and one signature. The first
identity entry is OPX enrolling itself with the key pinned in
`spec/contracts.toml [identity] opx_pub`. Every `enrol` carries the user's
proof of possession. A `grant` binds (UID, repo) to one role and one ssh
public key. Reading replays everything and refuses the whole file at the first
fault: a reordered, edited, missing or replayed line, or a foreign signer.

## 6. The GLYPH, the cover of the ssh keys

```text
"CGSG" | 1 | nonce (12) | ChaCha20-Poly1305(HKDF(IDSEED), keys + padding) | tag (16)
= 8 192 bytes = 256 × 256 bits
```

Only the login and password open it; one flipped bit makes it refuse. It holds
about 17 Ed25519 keys, one per (repo, role), and never says how many.

## 7. The cycle, command by command

```bash
# the register: .cgitsync/.memory/.register (ATCGS_REGISTER overrides it)
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX init     # once: prints idpub to pin
#   copy idpub into spec/contracts.toml [identity] opx_pub, then:
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX init     # OPX enrols itself
pixi run '@cgs' DEV request req.json github:flipoyo/atCGS DEV
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX admit req.json
pixi run '@cgs' DEV login cgs                    # cgs.cgs + DEV keys in a private agent
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX revoke <UID> github:flipoyo/atCGS
```

Every login and password is asked with `getpass`. `req.json` carries the
UID, IDPUB, the proof and the ssh public keys: nothing secret.

## 8. What each party sees

```text
UX         login, password, own GLYPH
session    IDSEED, ssh private keys, in memory; agent killed at close
OPX        UID, IDPUB, ssh public keys, roles
cgitsync   a .cgs and SSH_AUTH_SOCK
remote     an ssh public key
```

The role codes are ComplexGitSync's PoE vectors, 4-bit: OPX `0000` (OPX is POE),
DEV `1000`, USR `1100`, PUB `1111`. atCGS imports them, it does not define them.
PUB is the absence of a grant, never an entry.

## 9. The class KEY

```text
PUB DELTA POEX KEY
KEY OPX CGS PUB
```

Both stay `NAME NODE EDGE OP` records; KEY is no longer `sha256(GLYPH)`.

## 10. Inspect the contract

```bash
pixi run contract-inspect
```

Expected: `public_rows = 4`, `key_rows = 2`, `glyph_rows = 2`, `opx_pinned`
false until OPX's key is pinned. `[identity]` and `[glyph]` are compared with
the code (Argon2id cost, GLYPH layout, role codes): change one and it refuses.

## 11. Definition of success

The four tuples, the two KEY and the two GLYPH records are strictly preserved.
No login, password or private key is on disk after a session, and
`pixi run test` covers every refusal below.
Tutorial 06 gathers the checks and the 24 h schedule.

## Additional validation: cases to automate

- Tuple 0: `README` NAME, `atCGS` NODE, `USR` EDGE, `PUB` OP.
- Tuple 1: `DELTA` NAME, `POEX` NODE, `OPX` EDGE, `HASH` OP.
- Tuple 2: `HASH` NAME, `DELTA` NODE, `CGS` EDGE, `OPX` OP.
- Tuple 3: `.cgs` NAME, `USR` NODE, `PUB` EDGE, `.toml` OP.
- Every tuple: refuse swapped, deleted or case-normalised fields; no implicit PRIVATE.
- KEY: `PUB DELTA POEX KEY` and `KEY OPX CGS PUB` unchanged; no GLYPH hash.
- GLYPH: `NAME GLYPH POEX OPX` and `NAME GLYPH PUB .toml` unchanged.
- Identity: same inputs, same UID; the test profile never matches a real key.
- Journals: tamper, reorder, delete, replay, foreign signer, all refused.
- GLYPH: 8 192 bytes, fresh nonce, capacity refused at seal time.
- Session: agent gone after an exception; subprocess gets only `SSH_AUTH_SOCK`.
- Login: wrong password `AccessRefused`; `USR login` of a DEV-only UID exits 3.
- Publication: a GLYPH is never published, even sealed; PRIVATE stays out of PUB.

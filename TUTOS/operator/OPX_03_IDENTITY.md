# OPX 03 — Identity: journals, GLYPH and sessions

**Status: current (1.8.0-alpha).** Every command below runs; each is covered by a
test, by `identity-demo` / `local-remote`, or by OPX 01.

**Goal:** identify a user and open their ssh keys without ever storing a name or
a password (REFERENCE.md § 3). OPX 01 runs this cycle for OPX on the real tree; this
tutorial explains what each piece is.

## 1. Watch it work first

```bash
pixi run identity-demo --pbm-dir /tmp/glyphs
```

It builds OPX, alice (DEV) and bob (USR) in a temporary directory and prints
each step, ending with four refusals. Open `/tmp/glyphs/alice.pbm`: it is noise.

```bash
pixi run local-remote
```

The same against a real `sshd` on localhost, with two repositories: alice
pushes, bob only fetches, each key opens its own repository only, and bob's key
is refused as soon as OPX revokes it, even while it is loaded.

## 2. Identity: login, password → public key

```text
IDSEED = Argon2id(password, "atCGS/id/v1/" + profile + "/" + login)   memory only
IDPUB  = Ed25519 public key of IDSEED                                 registered
UID    = sha256(IDPUB)                                                the only name
```

The same login and password always give the same UID; one changed character
gives another. Nothing is looked up by login: the client recomputes the UID.
Anyone holding IDPUB can try passwords offline, so the Argon2id cost (256 MiB,
3 passes) and a long passphrase are the defence.

## 3. The two journals

```text
identity.jsonl   enrol | rotate | revoke    who exists       signed by OPX (enrol)
access.jsonl     grant | revoke             who may do what  signed by OPX only
```

They live in `.cgitsync/.memory/.register` (`ATCGS_REGISTER` overrides it), so a
`push --all` backs them up. Each line carries `prev = sha256(previous line)` and
one signature. The first identity entry is OPX enrolling itself with the key
pinned in `spec/contracts.toml [identity] opx_pub`. Every `enrol` carries the
user's proof of possession. A `grant` binds (UID, repo) to one role and one ssh
public key. Reading replays everything and refuses the whole file at the first
fault: a reordered, edited, missing or replayed line, or a foreign signer.

## 4. The GLYPH, the cover of the ssh keys

```text
"CGSG" | 1 | nonce (12) | ChaCha20-Poly1305(HKDF(IDSEED), keys + padding) | tag (16)
= 8 192 bytes = 256 × 256 bits
```

Only the login and password open it; one flipped bit makes it refuse. It holds
about 17 Ed25519 keys, one per (repo, role), and never says how many.

## 5. The cycle, command by command

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init     # once: prints idpub to pin
#   copy idpub into spec/contracts.toml [identity] opx_pub, then:
ATCGS_AUTHORIZE=OPX pixi run cgs OPX init     # OPX enrols itself
pixi run cgs DEV request req.json github:flipoyo/atCGS DEV
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit req.json
pixi run deploy-keys [--repo github:o/n]      # prints the gh api commands; OPX runs them
pixi run cgs DEV login cgs fetch              # DEV keys in a private agent, cgitsync fetch
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <UID> github:flipoyo/atCGS
```

Every login and password is asked with `getpass`. `req.json` carries the UID,
IDPUB, the proof and the ssh public keys: nothing secret.

## 6. What a login allows

| Level | cgitsync verbs through `login` |
|---|---|
| USR | `status`, `view-tree`, `fetch`, `pull`, `validate` |
| DEV | those, plus `add`, `rm`, `commit`, `push`, `branch`, `checkout`, `merge`, `autofix` |
| OPX | those, plus `tag`, `release`, `bootstrap`, `initialise`, `omniscience`, `memory`, `env`, `verify`, `unlock`, `self-history`, `promote` |

A verb outside the list is refused before anything runs. The remote enforces the
rest: a key is a deploy key of one repository only. `login` writes `TWIN.cgs`
only when run alone or for `bootstrap`/`initialise`, never inside a tracked repo.
A bare `login TWIN bootstrap` runs `bootstrap <twin>-<level>.cgs`, the command
ComplexGitSync's `LevelCommand` names. `promote DIR FROM TO` is not a cgitsync verb: it
fast-forwards branch TO of the one repository at DIR to FROM on its remote, with that
repository's key, and refuses anything that is not a fast-forward.

## 7. What each party sees

```text
UX         login, password, own GLYPH
session    IDSEED, ssh private keys, in memory; agent killed at close
OPX        UID, IDPUB, ssh public keys, roles
cgitsync   SSH_AUTH_SOCK and GIT_SSH_COMMAND, the session's ssh wrapper
remote     an ssh public key
```

The wrapper reads the repository from git's remote command and offers only that
repository's key, with `-F /dev/null` and `IdentitiesOnly`: nothing from
`~/.ssh` is used. The role codes are ComplexGitSync's PoE vectors: OPX `0000`
(OPX is POE), DEV `1000`, USR `1100`, PUB `1111`. PUB is the absence of a grant.

## 8. One identity, many projects

The register belongs to the project that holds atCGS. In the cgs workspace atCGS is the root:
that register is the **master**, and the only place where `OPX init`, `admit` of a new identity
and `revoke UID` work. In a tree that mounts atCGS read-only (`.atcgs` in
`examples/molo_*.cgs`) the register is that project's own, in its `.cgitsync/.memory/.register`.

```bash
# in the cgs workspace, once per new identity
ATCGS_AUTHORIZE=OPX pixi run cgs OPX publish
# → branch CGS-MOLO of .omniscience gets atcgs/identity.jsonl and atcgs/identity.head
```

`publish` opens an OPX session, writes the branch in a throwaway git worktree inside the session's
private directory, pushes it, and removes it: the checkout of `.omniscience` in the tree never moves.
It does nothing if the published head already equals the register's.

```bash
# in the MOLONARI tree, from its own atCGS
cd ~/.cgs/MOLONARI-<timestamp>/.atcgs
pixi install                                     # the root manifest: ComplexGitSync pinned
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit molo.json   # copies the identities, writes the grants
pixi run cgs OPX login MOLONARI fetch
```

Every `login` and `admit` first copies the published identities into the project register,
verified against the pinned OPX key. A copy that cannot be reproduced from the published file
(a line the published journal lacks) is refused, never merged. Grants (`access.jsonl`) are the
project's own: a user known to atCGS has no access to a project until OPX grants it there.

## 9. Inspect the contract

```bash
pixi run contract-inspect
```

Expected: `"status": "VALIDATED_SYNTAX"` and `"opx_pinned": true` once OPX's key
is pinned. `[identity]` and `[glyph]` are compared with the code (Argon2id cost,
GLYPH layout, role codes): change one and it refuses.

## 10. Definition of done

- `identity-demo` ends with four `REFUSED` lines; `local-remote` passes.
- No login, password or private key is on disk after a session.
- `pixi run test` covers the refusals: tampered, reordered, replayed or foreign
  journal lines; a flipped GLYPH bit; a wrong password (`AccessRefused`); a
  `USR login` of a DEV-only UID (exit 3); a verb outside the level's list.

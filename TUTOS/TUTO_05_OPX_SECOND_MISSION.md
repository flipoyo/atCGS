# TUTO 05 — OPX, the second mission: put a project under the gate

**Status: current (1.7.2-alpha).** Run on 2026-11-05 on `flipoyo/MOLONARI1D`,
branch `CGS-MOLO` (ticket MolonariCgsMolo). Outputs are the real ones, abridged.

**Goal:** administer a second project with `@cgs`. The project's tree mounts
atCGS **read-only** at `.atcgs`; that atCGS gates the project with the
project's **own register**. You publish the identities once, admit the keys in
the project's register, and make a first commit and push through the gate.

Read TUTO 01 first: it founds the master register and the first tree. TUTO 03
explains the journals; this one only uses them.

## 0. The idea in four lines

- **Identity is global.** Whoever the master register (the cgs workspace) enrols
  is known everywhere. OPX publishes the identity journal to `.omniscience`;
  every project's register copies it, verified against the pinned OPX key.
- **Access is local.** `access.jsonl` is the project's own: a known user has no
  access to a project until OPX grants it there.
- **Only the master enrols.** In a project register, `OPX init`, `publish`,
  `revoke UID` and admitting an unknown identity are refused.
- **No `~/.ssh`.** Every git operation after the install runs through the
  session's keys.

## 1. Before you start

- TUTO 01 done: OPX pinned and enrolled in the cgs workspace, `deploy-keys`
  known, `gh` logged in with admin on the project's repositories.
- A tree spec for the project **in atCGS**, `examples/<project>.cgs`:
  `examples/molonari.cgs` is the model. It declares the project's repositories on
  their branch, plus three mounts:
  - `.atcgs`: atCGS on `CGS-ALPHA`, `private = true` (read-only);
  - `.cgitsync/.memory`: `private = true, writable = true` (the register);
  - `.omniscience`: `private = true`, on `CGS-MOLO` (read-only).

  It declares **no `environment`**: cgitsync would rebuild the project's own
  `pixi.lock`. ComplexGitSync is not mounted: the gate's Pixi installs it.
  `pixi run cgitsync validate examples/molonari.cgs` prints `DECLARED`.
- GLYPH room: it holds 17 keys. The cgs tree used 10, MOLONARI 6, so MOLONARI
  fits at 16; a third project needs a larger GLYPH or one per project.

## 2. Publish the identities

In the cgs workspace:

```bash
ATCGS_AUTHORIZE=OPX pixi run -m @cgs '@cgs' OPX publish
# { "published": true, "branch": "CGS-MOLO", "lines": 1, "head": "678b66c2…" }
```

`publish` opens an OPX session and writes `atcgs/identity.jsonl` and
`atcgs/identity.head` on branch `CGS-MOLO` of `flipoyo/omniscience`, from a
throwaway git worktree in the session's private directory. Your `.omniscience`
checkout stays on its own branch. Run it again: `published` is false and
nothing changes. Run it after every new enrolment or revocation in the master.

## 3. Ask for the keys, one per repository

Still in the cgs workspace, so the GLYPH gets them. **Do not run `admit` here:**
the cgs register must not receive these grants.

```bash
pixi run -m @cgs '@cgs' OPX request molo.json \
  github:flipoyo/MOLONARI1D OPX     github:flipoyo/MOLONARI-API OPX \
  github:flipoyo/MOLONARI-data OPX  github:flipoyo/MOLONARI-hardware OPX \
  github:flipoyo/MOLONARI-gate OPX  github:flipoyo/MOLONARI-computo OPX
```

`molo.json` holds public keys only; add it to `.gitignore`.

## 4. Install the tree (the one step outside the gate)

```bash
pixi run cgitsync bootstrap examples/molonari.cgs MOLONARI
```

The gate does not exist before this, so this install uses your normal ssh, like
step 1 of TUTO 01. Nothing is written to the repositories, with one exception.
The install warns that `.memory` has no branch yet and asks `Run it now?
(y/N)`. Answer **`y`**: it creates the project's memory branch and pushes it.
The tree lands in `~/.cgs/MOLONARI-<timestamp>/`; `cd` into its `.atcgs`.

```text
fetched=…  .memory has no branch 'ComplexGitSync_MOLONARI_CGS-MOLO' yet … Run it now? (y/N) y
CGS-BOOTSTRAP … "tree_lifecycle_state": "READY"
```

The branch it creates there (`ComplexGitSync_<project>_<branch>`) is not the
one the later `checkout` uses (`<project>_<branch>`, here `MOLONARI_CGS-MOLO`):
the first stays an empty copy of `main`. Delete it when you are done (§ 9).

## 5. Install the gate

```bash
cd ~/.cgs/MOLONARI-<timestamp>/.atcgs
pixi install                     # the root manifest: ComplexGitSync pinned
pixi run test
```

The gate uses atCGS's root `pixi.toml`, which pins ComplexGitSync and never names
`./ComplexGitSync`. (Before 1.7.2-alpha the development environment shared that
manifest and this step needed `PIXI_FROZEN=true`.)

## 6. Grant, in the project's register

Still in `.atcgs`:

```bash
ATCGS_AUTHORIZE=OPX pixi run '@cgs' OPX admit ~/.cgs/<cgs-workspace>/molo.json
# granted: MOLONARI1D, -API, -data, -hardware, -gate, -computo  (role OPX)
```

This copies the published identity into the project's register
(`<tree>/.cgitsync/.memory/.register`) and writes the 6 grants there. Check:
the two `identity.jsonl` files are byte-identical; the cgs register's
`access.jsonl` is unchanged.

A session reaches **only** the repositories it holds a key for, read-only
mounts included. The tree also has atCGS, `.omniscience` and `.memory`. Their
keys already exist, so grant the same ones: build a request from the cgs
register's public data (the `grant` lines for those three repos in
`access.jsonl`: `repo`, `role`, `ssh`) and `admit` it the same way. No new key,
no new GitHub call.

## 7. Install the deploy keys

```bash
pixi run deploy-keys --repo github:flipoyo/MOLONARI1D --repo github:flipoyo/MOLONARI-API …   # the 6
```

It prints one `gh api` per named repository and runs nothing. Read them, run
them. Each answers with `"read_only": false`. A repository may already hold
other deploy keys (MOLONARI-API had one for a VPS): yours is added beside it.

## 8. Align, commit and push through the gate

```bash
pixi run '@cgs' OPX login MOLONARI fetch                 # fetched=9, "agent_keys": 9
pixi run '@cgs' OPX login MOLONARI checkout CGS-MOLO     # .memory → MOLONARI_CGS-MOLO
pixi run '@cgs' OPX login MOLONARI commit --all "message on one line"
pixi run '@cgs' OPX login MOLONARI push --all
# pushed MOLONARI: origin/CGS-MOLO (+1)      .memory pushed by its own fold
```

`--all` includes `.memory`, which holds the project's register: the push
backs it up. atCGS and `.omniscience` are read-only and never written; the
other repositories have nothing to commit. The first commit here was three
lines of `.gitignore` that cgitsync itself had added (`.atcgs`,
`.omniscience`, `MOLONARI.lgr`).

## 9. Check, and clean up

```bash
git -C ~/.cgs/MOLONARI-<timestamp> rev-parse --short HEAD
git ls-remote git@github.com:flipoyo/MOLONARI1D.git refs/heads/CGS-MOLO     # the same
gh api repos/flipoyo/MOLONARI1D/keys --jq '.[] | "\(.title) \(.last_used)"'
git -C ~/.cgs/MOLONARI-<timestamp>/.cgitsync/.memory ls-remote origin 'refs/heads/*MOLONARI*'
```

Delete the empty `ComplexGitSync_MOLONARI_CGS-MOLO` branch after checking it
points at the same commit as `main` (`gh api -X DELETE repos/flipoyo/.memory/git/refs/heads/<branch>`).

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `… is done in the master register` | `init`, `publish`, `revoke UID` or an unknown identity in a project | do it in the cgs workspace, then `publish` |
| `differs from the published one: refused` | the project register enrolled something the master never did | restore its `identity.jsonl` from `.omniscience/atcgs/` |
| `CGSHOME … is not the project this register belongs to` | `CGSHOME` names another tree | unset it, or `cd` into the project |
| `no key is granted for this repository` on a mount | atCGS, `.omniscience` or `.memory` not granted in the project register | § 6, last paragraph |
| `pixi.lock` of the project shows 7 000 changed lines | the spec declares an `environment` | remove it from the `.cgs`; `git checkout -- pixi.lock` |
| `branch misalignment … .memory` at commit | `.memory` still on `main` | `checkout CGS-MOLO` (§ 8) |

## Definition of done

- A commit on `origin/CGS-MOLO` of the project's root repository, pushed by
  the project's `@cgs`, and its deploy key's `last_used` set.
- The project register's `identity.jsonl` equals the published one; its
  `access.jsonl` holds the project's grants only.
- The project's other repositories are untouched.

**Next mission:** revoke an identity: `OPX revoke UID` in the cgs workspace,
`OPX publish`, and the project's next `login` copies the revocation (covered by
`test_a_revocation_reaches_the_project`; not yet run on the real tree).

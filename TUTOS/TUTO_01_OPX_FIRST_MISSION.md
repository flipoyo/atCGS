# TUTO 01 — OPX, the first mission

**Status: current (1.8.0-alpha).** Every command below was run on 2026-11-05 to
close the Dogfooding ticket. The outputs are the real ones, abridged.

**Goal:** you are OPX, the operator who holds the root of trust. Your first
mission is to make atCGS develop itself. You build the OPX tree, found the
register with your own key, give yourself one ssh key per repository, and make
the first commit and push of the tree through `@cgs`, with no key from `~/.ssh`.

When you are done:

- `spec/contracts.toml` pins your public key: OPX exists.
- `.cgitsync/.memory/.register` says which key may write which repository.
- Every everyday git operation goes through `pixi run -m @cgs '@cgs' OPX login …`.

## 0. What you need

- An atCGS clone, with Pixi installed.
- Admin rights on the GitHub repositories of `examples/cgs-opx.cgs`, and `gh`
  logged in. `gh` is used once, in step 5, to install deploy keys.
- A login and a long password for OPX. **Nothing stores them and you cannot
  recover them**: the same pair gives the same key, and you type it at every
  step that asks `OPX login:`.

## 1. Build the OPX tree

From the atCGS clone:

```bash
pixi run cgitsync bootstrap examples/cgs-opx.cgs cgs
```

This clones the tree into a new `~/.cgs/cgs-<timestamp>/`. That directory is
your workspace from now on: `cd` into it. The tree is atCGS at the root,
ComplexGitSync at `./ComplexGitSync`, and 8 more repositories (`.memory`,
`.omniscience`, `.agent/…`).

Check that the development manifest, `@cgs/pixi.toml`, sees both repositories live:

```bash
pixi run -m @cgs python -c "import ComplexGitSync; print(ComplexGitSync.__file__)"
# …/ComplexGitSync/src/ComplexGitSync/__init__.py
pixi run -m @cgs test        # passed, no failures
```

## 2. Create your identity

```bash
ATCGS_AUTHORIZE=OPX pixi run -m @cgs '@cgs' OPX init
```

It asks for your login and your password twice, then prints:

```json
{ "layer": "OPX", "uid": "35c6…d104", "idpub": "qL1F…DMo=", "pinned": false,
  "next": "copy idpub into spec/contracts.toml [identity] opx_pub, then run OPX init again" }
```

`idpub` is your public key. It is safe to show.

## 3. Pin it, and enrol

Copy `idpub` into `spec/contracts.toml`:

```toml
[identity]
opx_pub = "qL1FhYN4yQrRd6/cOa92zPG6rsu2t8JXirlntzsYDMo="
```

Then run `init` again with **the same** login and password:

```bash
ATCGS_AUTHORIZE=OPX pixi run -m @cgs '@cgs' OPX init
# { "layer": "OPX", "uid": "35c6…d104", "pinned": true, "enrolled": true }
```

The register now exists: `.cgitsync/.memory/.register/identity.jsonl`.
`does not match the pinned OPX key` means the pair differs from step 2.

## 4. One ssh key per repository

List every repository of the OPX tree, each with the role `OPX`:

```bash
pixi run -m @cgs '@cgs' OPX request req.json \
  github:flipoyo/atCGS OPX          github:flipoyo/ComplexGitSync OPX \
  github:flipoyo/omniscience OPX    github:flipoyo/.memory OPX \
  github:flipoyo/.ticketing OPX     github:flipoyo/DevSpec OPX \
  github:flipoyo/DocSpec OPX        github:flipoyo/.dev OPX \
  github:flipoyo/.localSpec OPX     github:flipoyo/.claude OPX
ATCGS_AUTHORIZE=OPX pixi run -m @cgs '@cgs' OPX admit req.json
```

`request` generates 10 keys and seals them in your GLYPH (outside the
repository). `req.json` holds only public keys and stays untracked. `admit`
prints one grant per repository, with its fingerprint, and writes `access.jsonl`.

## 5. Install the deploy keys on GitHub

```bash
pixi run -m @cgs deploy-keys
# 10 deploy key(s) from the access journal; review, then run:
# gh api repos/flipoyo/atcgs/keys -f 'title=atCGS OPX 35c65c668cb8' -f 'key=ssh-ed25519 …' -F read_only=false
```

The task only **prints** the commands: nothing calls GitHub on its own.
Review them, then run them. Each one answers with a JSON object carrying `"id"`.

## 6. Prove the keys, read-only

```bash
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync fetch
# fetched cgs: origin … fetched ComplexGitSync: origin
# fetched=10 skipped=0
# { …, "agent_keys": 10, "cgitsync": 0, "closed": true }
```

`login` opens your GLYPH, loads the keys into a private ssh-agent, and runs
`cgitsync fetch` through an ssh wrapper that offers each repository its own key
only. The agent is killed when the session closes.

## 7. Put the tree on its level branch

`cgs-opx.cgs` opens the project on branch `opx`, falling back to `CGS-ALPHA`.
On the first install `opx` exists nowhere, so every repository sits on its
fallback and `commit` refuses with `branch misalignment`. Create the branches:

```bash
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync checkout opx
```

```text
cgs (root) [ALIGNED] br=opx fb=CGS-ALPHA
├── .memory (leaf) [ALIGNED] br=ComplexGitSync_cgs_opx fb=main
├── omniscience (leaf) [ALIGNED] br=cgs_opx fb=main
└── ComplexGitSync (leaf) [ALIGNED] br=cgs_opx fb=CGS-ALPHA
```

ComplexGitSync is on `cgs_opx`, not `opx`: mounted in another project's level
tree, it always takes `<project>_<branch>` (cgitsync's `behind_gate` rule), so
two projects never share a branch of the tool. Uncommitted work comes along.

## 8. The first dogfooded commit and push

```bash
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync commit --all "cgs-1.7.1-alpha …"
# committed .memory: b7349e8…   committed cgs: 6a8589f…
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync push --all
# pushed cgs: origin/opx (upstream set) … pushed=6 skipped=1
```

`--all` includes the private, writable repositories: `.memory` holds your
register, so the push backs it up. The three read-only ones are never written.
Give the message on one line: `@cgs` does not keep a multi-line message.

## 9. Land it on CGS-ALPHA

`CGS-ALPHA` is the branch where atCGS and ComplexGitSync meet. It receives the
level's work by a merge:

```bash
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync merge opx --into CGS-ALPHA
# fast-forwarded cgs: CGS-ALPHA <- opx
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync checkout CGS-ALPHA
pixi run -m @cgs '@cgs' OPX login ComplexGraphSync push
# pushed ComplexGitSync: origin/cgs_CGS-ALPHA (upstream set)
# pushed cgs: origin/CGS-ALPHA (+1)
```

The `checkout` is needed: `merge` skips ComplexGitSync, which has no `opx`
branch, so it stays on `cgs_opx` and the push refuses until the tree is aligned
on `CGS-ALPHA` (ComplexGitSync on `cgs_CGS-ALPHA`). Leave `--all` out here: the
private repositories already pushed their level branches in step 8.

## 10. Check that `~/.ssh` played no part

Your own ssh probably reaches GitHub too, so a working push proves nothing by
itself:

```bash
ssh -T git@github.com
# Hi flipoyo! …             your personal key, through ~/.ssh/config
GIT_SSH_COMMAND="ssh -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes \
  -o IdentityAgent=none -o IdentityFile=/dev/null" git ls-remote origin
# git@github.com: Permission denied (publickey).    exit 128
gh api repos/flipoyo/atCGS/keys --jq '.[] | "\(.title) \(.last_used)"'
# atCGS OPX 35c65c668cb8 2026-11-05T10:51:08Z
```

Under the session's rules (`-F /dev/null`, `IdentitiesOnly`, no outside agent)
and without a session key, GitHub refuses. `last_used` shows the deploy key did
the work. GitHub does not refresh it at every use, so it can lag behind.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `unrecognized arguments: --all` | `fetch` has no `--all`; it covers the tree already | `… login ComplexGraphSync fetch` |
| `branch misalignment: expected 'cgs_opx'` at commit | the level branch does not exist yet | step 7 |
| `expected 'cgs_CGS-ALPHA', found 'cgs_opx'` at push | merged into `CGS-ALPHA` without aligning the tree | `checkout CGS-ALPHA`, then push |
| `no key is granted for this repository in this session` | the repository is not in your request | `request` it, `admit`, step 5 |
| `does not match the pinned OPX key` | another login or password | the pair of step 2 |

## Definition of done

- `contract-inspect` reports `opx_pinned` true.
- `… login ComplexGraphSync fetch` ends with `fetched=10` and `"cgitsync": 0`.
- Your commit is on `origin/CGS-ALPHA`, pushed by `@cgs`, and the check of § 10
  refuses without a session key.

**Next mission:** put a second project under the gate (TUTO 05), or admit a DEV. The DEV runs `@cgs DEV request` for the
repositories of `examples/cgs-dev.cgs`, you `admit` it, and the DEV bootstraps
`cgs-dev.cgs` (branch `dev`). TUTO 03 has the identity commands.

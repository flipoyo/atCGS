# TUTO 04 — Enrol a team in a project: a MOLONARI OPX, a DEV and a USR

**Written on 2026-11-06** (atCGS 1.9.1-alpha) from the code. These exact steps have not
been run with three people yet: the commands are the ones of TUTOS 01 and 02, which were run.

**Starting point.** One person is known to atCGS: the **owner**, who is also
**atCGS's OPX**, enrolled on 2026-11-05. Three newcomers have nothing yet: no profile, no
key. Here they are called *Alice*, *Bruno* and *Chloé*.

**What you get at the end:** on the MOLO-HRDW twin, Alice is its OPX, Bruno a DEV, Chloé
a USR. Each of them has an own copy of the twin and logs in with an own login and password.

## 0. First, the two meanings of "OPX"

They are not the same thing, and only one of them can admit people.

| | **atCGS OPX** | **project OPX** (e.g. MOLONARI's) |
|---|---|---|
| How many | **one** for the whole of atCGS: the key pinned in `spec/contracts.toml` `[identity] opx_pub` | as many as atCGS OPX grants, per project |
| What makes you one | your login and password give that pinned key | a grant with the role `OPX` in a project's register |
| Where it counts | everywhere: the master register and every project | in that project only (MOLO-HRDW ≠ MOLO-DATA) |
| `enrol`, `publish` (identities) | yes, in the master register | **no** |
| `admit`, `revoke` (rights in a project) | yes, from that project's gate | **no**: every line of a register is signed by atCGS OPX |
| Work on the project: `commit`, `push`, `tag`, `release`, `bootstrap`, `initialise`, `memory`, `promote`, `env`, … | yes, where it holds OPX grants | yes |

So in this tutorial: **you** (the owner) are atCGS OPX and do every enrolment and every
admission. **Alice** becomes MOLONARI's OPX: she runs the project, but she asks you when
someone must be admitted or removed.

> Not built yet: a project OPX who admits their own team. Today all admissions
> go through atCGS OPX.

**A project is a twin.** Each `.cgs` of `examples/` (MOLO-HRDW, MOLO-DATA, MOLO-CMPT,
MOLO-TWX) has its own register, so rights are given twin by twin. Here: MOLO-HRDW.
For another twin, repeat steps 3 to 5 from that twin's gate.

## 1. The three newcomers: register

Each of them follows [TUTO 01](TUTO_01_REGISTER.md), steps 0 to 3, on their own machine:
install Pixi and git, clone atCGS over https, choose a login and password, `request`,
send the request file to you. The only difference is what they ask for:

| Repository of MOLO-HRDW | Alice (project OPX) | Bruno (DEV) | Chloé (USR) |
|---|---|---|---|
| `github:flipoyo/MOLONARI-hardware` | OPX | DEV | USR |
| `github:flipoyo/.memory` | OPX | DEV | USR |
| `github:flipoyo/atCGS` | USR | USR | USR |
| `github:flipoyo/omniscience` | USR | USR | USR |

They ask for all four, even Chloé: a session reaches only the repositories it holds a key
for. `atCGS` and `omniscience` stay USR for everyone, Alice included: the gate and the
published identities are written by atCGS OPX only.

```bash
cd ~/atCGS
# Alice
pixi run cgs OPX request ~/alice-hrdw.json \
  github:flipoyo/MOLONARI-hardware OPX  github:flipoyo/.memory OPX \
  github:flipoyo/atCGS USR              github:flipoyo/omniscience USR
# Bruno
pixi run cgs DEV request ~/bruno-hrdw.json \
  github:flipoyo/MOLONARI-hardware DEV  github:flipoyo/.memory DEV \
  github:flipoyo/atCGS USR              github:flipoyo/omniscience USR
# Chloé
pixi run cgs USR request ~/chloe-hrdw.json \
  github:flipoyo/MOLONARI-hardware USR  github:flipoyo/.memory USR \
  github:flipoyo/atCGS USR              github:flipoyo/omniscience USR
```

The word after `cgs` (`OPX`, `DEV`, `USR`) only labels the prompts. It asks for nothing:
what is asked is the role written after each repository.

Each one writes down the `uid` printed and sends you the request file (it is public).
Ask them for their `uid` by a second channel, a phone call for instance: it is how you
know a file is really theirs.

## 2. You (atCGS OPX): enrol the three identities

In your own workspace, the one with the master register (TUTO 01 step 4):

```bash
ATCGS_AUTHORIZE=OPX pixi run cgs OPX enrol ~/requests/alice-hrdw.json
ATCGS_AUTHORIZE=OPX pixi run cgs OPX enrol ~/requests/bruno-hrdw.json
ATCGS_AUTHORIZE=OPX pixi run cgs OPX enrol ~/requests/chloe-hrdw.json
ATCGS_AUTHORIZE=OPX pixi run cgs OPX publish
```

Each `enrol` asks **your** OPX login and password, checks the `uid` against what the
person told you, and grants nothing. `publish` puts the three new identities in
`.omniscience`, where every twin reads them.

## 3. You: admit them in the project

From the gate of **your** copy of MOLO-HRDW (installed in [TUTO 02](TUTO_02_TWIN.md),
steps 2 to 4):

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs OPX login MOLO-HRDW pull                    # the identities you just published
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/requests/alice-hrdw.json
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/requests/bruno-hrdw.json
ATCGS_AUTHORIZE=OPX pixi run cgs OPX admit ~/requests/chloe-hrdw.json
```

Each `admit` prints the four grants it wrote in MOLO-HRDW's register. That is the moment
Alice becomes MOLONARI's OPX on MOLO-HRDW: her grants say `OPX`.

## 4. You: put their keys on GitHub

```bash
pixi run deploy-keys --repo github:flipoyo/MOLONARI-hardware --repo github:flipoyo/.memory \
  --repo github:flipoyo/atCGS --repo github:flipoyo/omniscience
```

It prints one `gh api …/keys` command per grant and runs nothing. Keep the lines of the
three newcomers (title `atCGS <ROLE> <first 12 characters of the uid>`), read them, run
them. USR keys are installed **read-only**, so GitHub itself refuses a push from Chloé, or
from anyone on `atCGS` and `omniscience`.

## 5. You: push the register

The grants are in your copy only, in `.cgitsync/.memory/.register`. The others' copies
read them from GitHub, so push the twin's memory:

```bash
pixi run cgs OPX login MOLO-HRDW commit --all "admit MOLONARI OPX, DEV and USR on MOLO-HRDW"
pixi run cgs OPX login MOLO-HRDW push --all
```

`--all` includes `.memory`. No `'` in the message (REFERENCE § 8).

## 6. The three newcomers: install their copy and log in

Each one, **after step 5**, follows [TUTO 02](TUTO_02_TWIN.md) step 7 (install a copy of the
twin with no key, over https), then checks with their own level:

```bash
cd ~/.cgs/MOLO-HRDW-<timestamp>/.atcgs
pixi run cgs OPX login MOLO-HRDW fetch      # Alice
pixi run cgs DEV login MOLO-HRDW fetch      # Bruno
pixi run cgs USR login MOLO-HRDW fetch      # Chloé
# fetched=4 skipped=0   "agent_keys": 4   "closed": true
```

Here the word after `cgs` matters: it is the level the session runs at, and the register
must hold a grant of that level for this person (`this UID holds no DEV grant` otherwise).

> A USR login has not been run on a real twin yet (REFERENCE § 8). If Chloé's fails,
> tell atCGS OPX what it prints.

## 7. What each one can now do on MOLO-HRDW

| | Alice (project OPX) | Bruno (DEV) | Chloé (USR) |
|---|---|---|---|
| `status`, `view-tree`, `fetch`, `pull`, `validate` | yes | yes | yes |
| `add`, `rm`, `commit`, `push`, `branch`, `checkout`, `merge`, `autofix` | yes | yes | no |
| `tag`, `release`, `bootstrap`, `initialise`, `memory`, `promote`, `env`, `verify`, `unlock`, `self-history` | yes | no | no |
| `admit`, `revoke`, `enrol`, `publish` | **no**: ask atCGS OPX | no | no |
| on MOLO-DATA, MOLO-CMPT, MOLO-TWX | nothing until admitted there | same | same |

Bruno's first change is [TUTO 03](TUTO_03_SUBTWINS.md).

## 8. Later: someone leaves, someone arrives

All of it is done by atCGS OPX.

```bash
# one right on this twin: from the twin's gate, then push as in step 5
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid> github:flipoyo/MOLONARI-hardware
# the person, everywhere: in your workspace (master register), then OPX publish
ATCGS_AUTHORIZE=OPX pixi run cgs OPX revoke <uid>
```

Also delete that person's deploy keys on GitHub (`gh api repos/flipoyo/<repo>/keys`):
revoking in the register does not remove them. A new member starts again at step 1.

## If something goes wrong

| You see | Who | Why | Do |
|---|---|---|---|
| `this login/password is not OPX's pinned key` | Alice, at `admit` | only atCGS OPX admits | send the request file to atCGS OPX |
| `enrolling a new identity is done in the master register` | you, at `admit` | the twin has not seen the published identity yet | `OPX login MOLO-HRDW pull`, then `admit` again |
| `this UID holds no OPX grant` (or DEV, USR) | a newcomer | wrong level after `cgs`, a typo in the login or password, or a copy installed before step 5 | the level of the table, retype slowly, or the next line |
| a copy installed before step 5 does not see the grants | a newcomer | its `.memory` is older than the push | `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf GIT_CONFIG_VALUE_0=git@github.com: git -C ~/.cgs/MOLO-HRDW-<timestamp>/.cgitsync/.memory pull` |
| `Permission denied (publickey)` at `login` | a newcomer | the deploy key is not on GitHub | step 4 |
| `USR may not run 'push' through login` | Chloé | USR reads only | ask for DEV |

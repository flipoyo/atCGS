# TUTO 01 — BIOS / BOOT / CGS ALPHA

**Goal:** reproduce the initial anchoring without modifying ComplexGitSync.
**Prerequisites:** Pixi (`pixi install` once); a terminal; no GitHub token.
**Indicative lab duration:** depends on the environment, not guaranteed.
**Deliverable:** a checked BIOS table and the `DECLARED_ONLY` status.

## A. Identify the kernel

The user entry is `atCGS`, the protocol version `1.2.0-alpha`.
The engine is `ComplexGitSync M.m.p`, to be pinned during an integration.
The initial invariant proposed in the thread was:

```text
BIOS BOOT CGS M.m.p
CGS L0 TIME POEX
```

This historical notation defines no timestamp or signature format.
Do not substitute a local clock for a verified proof of existence.

## B. Canonical BIOS step

```text
atCGS ALPHA BIOS ComplexGitSync M.m.p
ComplexGitSync G POEX .gts
.gts G OPX TWX
TWX ENV HWX DEV
DEV HWX TWX USR
USR TWX G .cgs
```

The first line has five tokens: it is the boot identity.
The next five have exactly four tokens, per PRIME G.
The spelling `M.m.p` is not replaced in the canonical document.
`POEX` is a frontier symbol, not a signed attestation.

## C. Earlier versions kept

```text
BIOS ENV HWX TWX
BOOT TWX POEX CGS
CGS POEX TWX GTS
GTS TWX OPX DEV
DEV HWX ENV USR
USR TWX GTS TWX
OPX HWX ENV TWX
```

These tuples are kept for design reproducibility.
The last `TWX` of the `USR` tuple is not a duplication error.
A future revision must specify how the BIOS calls the BOOT.

## D. Check the fixtures

```bash
pixi run contract-inspect
```

Look for `bios_new_rows = 5` and `bios_history_rows = 7`.
The check rejects any mutation of the tuples present in the TOML.
This command launches no remote Git operation.

## E. Examine the normative data

```bash
pixi run python - <<'PY'
import tomllib
with open('spec/contracts.toml','rb') as f:
    spec=tomllib.load(f)
print(spec['boot']['identity'])
for row in spec['boot']['current']:
    print(*row)

PY
```

This inspection is local: it opens neither a GitRepo nor a socket.

## Additional validation: cases to automate

- **ALPHA** `ComplexGitSync G POEX .gts`: check the literal sequence.
- **ALPHA** `ComplexGitSync G POEX .gts`: remove a field and expect a refusal.
- **ALPHA** `ComplexGitSync G POEX .gts`: swap fields 2 and 3 and expect a refusal.
- **ALPHA** `ComplexGitSync G POEX .gts`: change the case and expect a refusal.
- **ALPHA** `.gts G OPX TWX`: check the literal sequence.
- **ALPHA** `.gts G OPX TWX`: remove a field and expect a refusal.
- **ALPHA** `.gts G OPX TWX`: swap fields 2 and 3 and expect a refusal.
- **ALPHA** `.gts G OPX TWX`: change the case and expect a refusal.
- **ALPHA** `TWX ENV HWX DEV`: check the literal sequence.
- **ALPHA** `TWX ENV HWX DEV`: remove a field and expect a refusal.
- **ALPHA** `TWX ENV HWX DEV`: swap fields 2 and 3 and expect a refusal.
- **ALPHA** `TWX ENV HWX DEV`: change the case and expect a refusal.
- **ALPHA** `DEV HWX TWX USR`: check the literal sequence.
- **ALPHA** `DEV HWX TWX USR`: remove a field and expect a refusal.
- **ALPHA** `DEV HWX TWX USR`: swap fields 2 and 3 and expect a refusal.
- **ALPHA** `DEV HWX TWX USR`: change the case and expect a refusal.
- **ALPHA** `USR TWX G .cgs`: check the literal sequence.
- **ALPHA** `USR TWX G .cgs`: remove a field and expect a refusal.
- **ALPHA** `USR TWX G .cgs`: swap fields 2 and 3 and expect a refusal.
- **ALPHA** `USR TWX G .cgs`: change the case and expect a refusal.
- **BIOS** `BIOS ENV HWX TWX`: check the literal sequence.
- **BIOS** `BIOS ENV HWX TWX`: remove a field and expect a refusal.
- **BIOS** `BIOS ENV HWX TWX`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `BIOS ENV HWX TWX`: change the case and expect a refusal.
- **BIOS** `BOOT TWX POEX CGS`: check the literal sequence.
- **BIOS** `BOOT TWX POEX CGS`: remove a field and expect a refusal.
- **BIOS** `BOOT TWX POEX CGS`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `BOOT TWX POEX CGS`: change the case and expect a refusal.
- **BIOS** `CGS POEX TWX GTS`: check the literal sequence.
- **BIOS** `CGS POEX TWX GTS`: remove a field and expect a refusal.
- **BIOS** `CGS POEX TWX GTS`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `CGS POEX TWX GTS`: change the case and expect a refusal.
- **BIOS** `GTS TWX OPX DEV`: check the literal sequence.
- **BIOS** `GTS TWX OPX DEV`: remove a field and expect a refusal.
- **BIOS** `GTS TWX OPX DEV`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `GTS TWX OPX DEV`: change the case and expect a refusal.
- **BIOS** `DEV HWX ENV USR`: check the literal sequence.
- **BIOS** `DEV HWX ENV USR`: remove a field and expect a refusal.
- **BIOS** `DEV HWX ENV USR`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `DEV HWX ENV USR`: change the case and expect a refusal.
- **BIOS** `USR TWX GTS TWX`: check the literal sequence.
- **BIOS** `USR TWX GTS TWX`: remove a field and expect a refusal.
- **BIOS** `USR TWX GTS TWX`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `USR TWX GTS TWX`: change the case and expect a refusal.
- **BIOS** `OPX HWX ENV TWX`: check the literal sequence.
- **BIOS** `OPX HWX ENV TWX`: remove a field and expect a refusal.
- **BIOS** `OPX HWX ENV TWX`: swap fields 2 and 3 and expect a refusal.
- **BIOS** `OPX HWX ENV TWX`: change the case and expect a refusal.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p`: check the literal sequence.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p`: remove a field and expect a refusal.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p`: swap fields 2 and 3 and expect a refusal.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p`: change the case and expect a refusal.
- Check the BOOT: no private path is published.
- Check the BOOT: no checkpoint is fabricated.
- Check the BOOT: no GitRepo is cloned.
- Check the BOOT: no command is interpreted as a tuple.
- Check the BOOT: no transition is executed.
- Check the BOOT: the source keeps the TOML format.
- `M.m.p` must be pinned before a real boot.
- The BOOT fixture contains no secret.
- An empty field makes the identity non-compliant.
- The L0 proof stays separate from the local clock.
- The current table has five four-field tuples.
- The earlier table has seven.
- `GTS` stays distinct from `.gts`.
- The repetition of TWX is normative.
- PRIVATE rights do not derive from the shape of the tuples.
- No repository clone is executed.
- A new version requires a documented change.

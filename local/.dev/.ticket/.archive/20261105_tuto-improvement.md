It is impossible to follow the tuto. The explanation are very poor. It also comes from the README.md that is not USER oriented. Reformat everything around MOLONARI examples in README.md. atCGS is the GATE of an Operating Space synchronised with complexGitSync. It automatically recognises system profiles and their associated rights on GitRepo related to the operating space. @cgs is the identity manager of ComplexGitSync and therefore acts almost as a decorator. 

@cgs is a gate for every digitral twin based on git repository only. By construction, those twins contains their own memory which are their state-space. They are fully deterministic feature recomposable everywhere anytime

Tuto should presents 1. user registration
2. Twin emulation (MOLONARI)
3. MAnipulation a Twin with each part being a subtwin. MOLONARI has to be reduced to MOLO-HRDW (HardWare) MOLO-DATA MOLO-CMPT (computo) MOLO-TWX 
## Closed — 2026-11-05 (atCGS 1.9.0-alpha)

- **README.md** is user-oriented: atCGS as the gate of an Operating Space, @cgs as
  ComplexGitSync's identity manager, twins made of Git repositories with their own
  memory, MOLONARI as the running example, profiles and rights, a quick start.
  Its former technical content is `TUTOS/operator/REFERENCE.md` (sections kept;
  code and specs cite `REFERENCE.md § N`).
- **MOLONARI reduced to four twins**, each its own `.cgs` with its own gate and
  register: `examples/molo_hrdw.cgs` (MOLO-HRDW), `molo_data.cgs` (MOLO-DATA),
  `molo_cmpt.cgs` (MOLO-CMPT), and `molo_twx.cgs` (MOLO-TWX, the access point:
  MOLONARI1D with the three). Underscores, because `molo-twx.cgs` reads as project
  `molo`, branch `twx` (LinkAtCGS §7). `examples/molonari.cgs` is removed.
- **Three tutorials, each from a real run on 2026-11-05:** TUTO 01 register (a test
  DEV, UID `e9b6c66e…`), TUTO 02 emulate a twin (MOLO-HRDW, MOLO-TWX), TUTO 03 work
  through subtwins (DEV commit `772530e` on MOLONARI-hardware, seen in MOLO-TWX's
  `hardware/`). The former TUTO 01-05 are `TUTOS/operator/OPX_01..05`.
- **Code the runs needed:** `OPX enrol` (identity only, master register); sessions
  also load their UID's read-only USR grants; a forbidden `login` operation is
  named with what the profile may run.

Follow-ups, not done:
- A twin copies identities from its local `.omniscience` checkout: after `publish`,
  `pull` the twin first. `admit` could fetch it, or say it is behind.
- Pixi quotes task arguments with `'` and does not escape them: no apostrophe in a
  commit message.
- A DEV's `.memory` key is a deploy key of the whole memory repository.
- The install's `memory branch` offer names `ComplexGitSync_<TWIN>_CGS-MOLO`. In
  MOLO-HRDW and MOLO-TWX that branch is the one in use; in the MOLONARI tree
  `checkout` moved to `MOLONARI_CGS-MOLO`. Not stray here: nothing deleted.

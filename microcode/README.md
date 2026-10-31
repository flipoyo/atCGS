# atCGS 1.2.1-alpha — POEX and EOPX monolithic C microcodes

Two microcodes, two purposes:

- `poex`, Proof of Existence: its only purpose is comparing two GLYPHs.
- `eopx`, Existence of Proof: the birth protocol, turning a SEED into a GLYPH.

The Python classes `atcgs.POEX` and `atcgs.EOPX` wrap them. A GLYPH lives only in
those processes and their pipes: nobody stores it, and neither microcode writes it
anywhere but the wallet's pipe.

## Owner-defined interface

```text
poex is cgitsync M.m.p opx
OpFrontier serves POEX NODE DELTA OPX
```

The lowercase `poex` microcode is declared as part of `cgitsync M.m.p` at `opx`. The uppercase `POEX` belongs to the four-field requestable descriptor served by `OpFrontier`: `{POEX,NODE,DELTA,OPX}`. `atCGS` holds a monolithic **reference** implementation; it does not become a second GitTree/Merkle engine or authenticate a public proof. The `--contract` option displays these two descriptors without reading a matrix. The Python `OpFrontier.serve_poex()` method returns the static descriptor only, without executing CGS.

## poex: System specification

- `Layer 0 = POE`: a permanent, zero-initialized `System.layer0` state.
- `System.poe` is the stable address of `System.layer0.last4`. The **low four bits** of the `uint8_t` are the quartet (`0..15`); C cannot form an address to a four-bit primitive directly. No pointer to transient stack data is returned.
- `OpLayer(System*, uint8_t next4)` is the only mutation point. It ingests precisely **four bits**, increments the cumulative zero count and quartet count, sets `∆ELTA`, and returns `System.poe`.
- `∆ELTA(t) = .poe(t) XOR .poe(t-1)`, nibble valued `0..15`. The boot/genesis quartet is `0000`, so the first delta equals the first received quartet. This definition describes bit changes; it is independent of the **DELTA** graph identity.
- Real-time display = `fflush(stdout)` synchronously after each quartet is processed. It makes **no hard real-time latency guarantee** and does not invoke network, timer, dynamic allocation, or threads.
- Binary input: **2 × 8192 bytes**, GLYPH A then GLYPH B, each exactly **256 rows × 256 bits**, row-major with most-significant-bit-first within each byte. A is held in a static buffer, zeroed after use; each quartet ingested is `A XOR B`, high nibble then low nibble.
- Verdict: A and B are equal if and only if `zeros = 65536`. `atcgs.POEX` takes it back as the 4-bit `.poe`: equal is `0000`, different `1111`. The last line is `POEX COMPARED: ...; equal=yes|no; evidence=UNVERIFIED`; exit `0` when equal, `1` when different, `2` on a wrong input size.
- Packet framing: **64 packets × 128 bytes = 64 × (4 × 256 bits)**. Each packet contains 256 quartets; the whole matrix has 16,384 quartets. `.poe` reports are emitted for every quartet regardless of display mode.
- The state is *process-lifetime persistent*, not reboot persistent. This program does **not** perform a genuine PoE verification, Merkle hashing, hashing of any kind, authentication, GitTree operation or PUBLIC publication. The output is `UNVERIFIED` and cannot authorize `.omniscience` disclosure.
- External surface: reads the two raw matrices from `stdin` and writes only numeric counters/quartet changes to `stdout`. Raw matrix contents should be considered PRIVATE and no `--trace` output should automatically be treated as public.

## eopx: the birth protocol

- Input: a SEED on `stdin`, a square `.bit` of at least 256×256 bits (and at most 8192×8192). Anything else is refused with exit `2` and nothing on `stdout`.
- Output: the GLYPH, `SHAKE-256(SHA-256(SEED) || SEED)` truncated to 8192 bytes = 256×256 bits, on `stdout`, for the wallet's pipe only.
- Deterministic, from the initial value `hash(SEED)`. It always compresses, even a 256×256 SEED, so `hash(GLYPH) != hash(SEED)`.
- SHA-256 (FIPS 180-4) and SHAKE-256 (FIPS 202) are written in the file; no library is linked. The tests check the output against Python's `hashlib`.
- The SEED buffer and the GLYPH are zeroed before exit.

## Build

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -o poex poex.c
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -o eopx eopx.c
```

## Demo / use

```sh
pixi run python -c 'import sys;sys.stdout.buffer.write(bytes([0xA5])*8192)' > demo.bit
./eopx < demo.bit > a.glyph             # birth: SEED -> GLYPH (lab only; keep it off disk in real use)
cat a.glyph a.glyph | ./poex --packet   # 64 display updates, then equal=yes, exit 0
cat a.glyph demo.bit | ./poex --trace | head -n 5  # inspect the A XOR B stream
pixi run microcode-test                 # compiler + poex and eopx regression tests
```

## Boundary and limitations

`PRIME CGS = {OPX, DEV, USR, PUB}` remains a **separate** execution frontier. A real ".poe" output at Layer 0 must be checked and anchored before any publication in `.omniscience`. Only POEX and EOPX handle GLYPH bytes, in memory; `.cgitsync` and `.omniscience` see only hashes. A zero count or a quartet XOR cannot serve as a cryptographic identity or resistance claim.

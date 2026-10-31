# atCGS 0.2.2-alpha — POEX monolithic C microcode

## Owner-defined interface

```text
poex is cgitsync M.m.p opx
OpFrontier serves POEX NODE DELTA OPX
```

The lowercase `poex` microcode is declared as part of `cgitsync M.m.p` at `opx`. The uppercase `POEX` belongs to the four-field requestable descriptor served by `OpFrontier`: `{POEX,NODE,DELTA,OPX}`. `atCGS` holds a monolithic **reference** implementation; it does not become a second GitTree/Merkle engine or authenticate a public proof. The `--contract` option displays these two descriptors without reading a matrix. The Python `OpFrontier.serve_poex()` method returns the static descriptor only, without executing CGS.

## System specification

- `Layer 0 = POE`: a permanent, zero-initialized `System.layer0` state.
- `System.poe` is the stable address of `System.layer0.last4`. The **low four bits** of the `uint8_t` are the quartet (`0..15`); C cannot form an address to a four-bit primitive directly. No pointer to transient stack data is returned.
- `OpLayer(System*, uint8_t next4)` is the only mutation point. It ingests precisely **four bits**, increments the cumulative zero count and quartet count, sets `∆ELTA`, and returns `System.poe`.
- `∆ELTA(t) = .poe(t) XOR .poe(t-1)`, nibble valued `0..15`. The boot/genesis quartet is `0000`, so the first delta equals the first received quartet. This definition describes bit changes; it is independent of the **DELTA** graph identity.
- Real-time display = `fflush(stdout)` synchronously after each quartet is processed. It makes **no hard real-time latency guarantee** and does not invoke network, timer, dynamic allocation, or threads.
- Binary input: **8192 bytes**, representing exactly **256 rows × 256 bits**, row-major with most-significant-bit-first within each byte. On each byte, high nibble then low nibble.
- Packet framing: **64 packets × 128 bytes = 64 × (4 × 256 bits)**. Each packet contains 256 quartets; the whole matrix has 16,384 quartets. `.poe` reports are emitted for every quartet regardless of display mode.
- The state is *process-lifetime persistent*, not reboot persistent. This program does **not** perform a genuine PoE verification, Merkle hashing, SHA-256, authentication, GitTree operation or PUBLIC publication. The output is `UNVERIFIED` and cannot authorize `.omniscience` disclosure.
- External surface: reads raw matrix from `stdin` and writes only numeric counters/quartet changes to `stdout`. Raw matrix contents should be considered PRIVATE and no `--trace` output should automatically be treated as public.

## Build

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -o poex poex.c
```

## Demo / use

```sh
pixi run python -c 'import sys;sys.stdout.buffer.write(bytes([0xA5])*8192)' > demo.bit
./poex --packet < demo.bit          # 64 display updates, one per 4×256 packet
./poex --trace < demo.bit | head -n 5  # inspect 4-bit stream (broken pipe may exit early)
./poex < demo.bit                   # 16,384 carriage-return live updates
pixi run microcode-test           # compiler + 7 deterministic regression tests
```

## Boundary and limitations

`PRIME CGS = {OPX, DEV, USR, PUB}` remains a **separate** execution frontier. A real ".poe" output at Layer 0 must be checked and anchored before any publication in `.omniscience`. PRIVATE `.computo` may handle `.bit` bytes; the C microcode merely counts and compares them. A zero count or a quartet XOR cannot serve as a cryptographic identity or resistance claim.

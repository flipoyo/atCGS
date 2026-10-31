# TUTO 04 — POEX: 256×256 matrix and 4×256 packets

**Goal:** generate and verify an ordered binary commitment.

## 1. Starting matrix

```text
M = 256 × 256 bits
M = 65 536 bits = 8 192 bytes
1 row = 256 bits = 32 bytes
```

The binary is read row by row, most significant bit first.
A lab `.bit` file is a raw 8 192-byte file.
It is neither a PNG nor an attested public key.

## 2. POEX sequencing

```text
POEX[k] = (W[4k], W[4k+1], W[4k+2], W[4k+3])
0 <= k < 64
1 packet = 4 × 256 bits = 128 bytes
64 × 128 = 8 192 bytes
```

Reassembly in index order yields exactly the matrix.
A truncated, extra or swapped packet must be refused.

## 3. `.poe` invariant

A report is emitted after each four-bit quartet.
A packet contains 256 quartets; the matrix contains 16 384.
The counter records the number of zeros encountered.
The logical reference to the last quartet is kept in the simulation.
The Rust `.poe` memory pointer is not implemented in this lab.

## 4. Run the demonstrator

```bash
pixi run poex-candidate
```

Without `--input`, it produces a deterministic synthetic matrix.
The output contains a candidate root but no existence signature.

## 5. Test with a real lab matrix

```bash
pixi run python scripts/poex_4x256_simulator.py \
  --input fixtures/demo_256x256.bit --output from_bit.json
```

The roots of both commands must match.
The `.bit` file is synthetic, not taken from a real GitTree.

## 6. Proof verification

```bash
pixi run test
```

The tests check the reassembly of the 64 packets.
All 64 Merkle inclusion proofs are verified.
A bit flip is detected; so is an index permutation.
The index is part of the commitment of a packet leaf.

## 7. Cryptographic interpretation

A Merkle root commits to the chosen sequence of packets.
It establishes neither the identity of their author nor their date of existence.
An inclusion proof is not a publication authorisation.
The POEX SHA-256 domain is distinct from that of the `.gts` GitTree.

## 8. Expected output

```text
matrix_bits: 65536
packets: 64
bits_per_packet: 1024
nibble_reports: 16384
published: false
```

Tutorial 05 places the commitment at the USR/PUB frontier.

## Additional validation: cases to automate

- Packet 0: index encoded and authenticated in the leaf.
- Packet 0: a size of 128 bytes is required.
- Packet 0: 256 quartet reports expected.
- Packet 0: first row = 0.
- Packet 0: last row = 3.
- Packet 1: index encoded and authenticated in the leaf.
- Packet 1: a size of 128 bytes is required.
- Packet 1: 256 quartet reports expected.
- Packet 1: first row = 4.
- Packet 1: last row = 7.
- Packet 2: index encoded and authenticated in the leaf.
- Packet 2: a size of 128 bytes is required.
- Packet 2: 256 quartet reports expected.
- Packet 2: first row = 8.
- Packet 2: last row = 11.
- Packet 7: index encoded and authenticated in the leaf.
- Packet 7: a size of 128 bytes is required.
- Packet 7: 256 quartet reports expected.
- Packet 7: first row = 28.
- Packet 7: last row = 31.
- Packet 15: index encoded and authenticated in the leaf.
- Packet 15: a size of 128 bytes is required.
- Packet 15: 256 quartet reports expected.
- Packet 15: first row = 60.
- Packet 15: last row = 63.
- Packet 31: index encoded and authenticated in the leaf.
- Packet 31: a size of 128 bytes is required.
- Packet 31: 256 quartet reports expected.
- Packet 31: first row = 124.
- Packet 31: last row = 127.
- Packet 32: index encoded and authenticated in the leaf.
- Packet 32: a size of 128 bytes is required.
- Packet 32: 256 quartet reports expected.
- Packet 32: first row = 128.
- Packet 32: last row = 131.
- Packet 47: index encoded and authenticated in the leaf.
- Packet 47: a size of 128 bytes is required.
- Packet 47: 256 quartet reports expected.
- Packet 47: first row = 188.
- Packet 47: last row = 191.
- Packet 62: index encoded and authenticated in the leaf.
- Packet 62: a size of 128 bytes is required.
- Packet 62: 256 quartet reports expected.
- Packet 62: first row = 248.
- Packet 62: last row = 251.
- Packet 63: index encoded and authenticated in the leaf.
- Packet 63: a size of 128 bytes is required.
- Packet 63: 256 quartet reports expected.
- Packet 63: first row = 252.
- Packet 63: last row = 255.
- Case all-zero: compute or refuse the expected result.
- Case all-one: compute or refuse the expected result.
- Case single-bit: compute or refuse the expected result.
- Case swapped-index: compute or refuse the expected result.
- Case truncated: compute or refuse the expected result.
- Case extra-packet: compute or refuse the expected result.
- Case changed-root: compute or refuse the expected result.
- Case wrong-branch: compute or refuse the expected result.
- Case wrong-digest: compute or refuse the expected result.
- The `.bit` file is exactly 8 192 bytes.
- Packet 0 starts at row 0.
- Packet 63 ends at row 255.
- Each leaf commits to the packet index.

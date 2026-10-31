#!/usr/bin/env python3
"""atCGS (ComplexGraphSync SemVer): deterministic POEX 256x256 -> 64 x (4x256) simulator.

This is an *offline simulation*. It never writes to real .computo/.omniscience,
never executes cgitsync, never publishes or certifies a Proof of Existence.
A POEX Merkle commitment is not a signed existence checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atcgs import SYSTEM, require_pixi  # noqa: E402  # inner SemVer, single source of truth

# Wire-format schema id and hash domain-separation prefix (see leaf/node
# digests and ComplexGitSync#193), NOT the product SemVer: frozen, never bump.
VERSION = "CGS-POEX/0.0.0"
ROWS = 256
BITS_PER_ROW = 256
ROWS_PER_PACKET = 4
BYTES_PER_ROW = BITS_PER_ROW // 8
BYTES_PER_PACKET = ROWS_PER_PACKET * BYTES_PER_ROW
PACKETS = ROWS // ROWS_PER_PACKET
BITS_PER_NIBBLE = 4

# Owner-provided literals. Four-field ontological tuples are *not* binary payloads.
BOOTSTRAP = (
    ("BIOS", "ENV", "HWX", "TWX"),
    ("BOOT", "TWX", "POEX", "CGS"),
    ("CGS", "POEX", "TWX", "GTS"),
    ("GTS", "TWX", "OPX", "DEV"),
    ("DEV", "HWX", "ENV", "USR"),
    ("USR", "TWX", "GTS", "TWX"),
    ("OPX", "HWX", "ENV", "TWX"),
)
ALPHA = (
    ("ComplexGitSync", "G", "POEX", ".gts"),
    (".gts", "G", "OPX", "TWX"),
    ("TWX", "ENV", "HWX", "DEV"),
    ("DEV", "HWX", "TWX", "USR"),
    ("USR", "TWX", "G", ".cgs"),
)
DELTA_NABLA = (
    ("DELTA", "POEX", "NABLA", "OPX"),
    ("OPX", "ENV", "PRIME", "DELTA"),
    ("DELTA", "ENV", "PRIME", "NABLA"),
    ("NABLA", "EDGE", "POEX", "OPX"),
)
OPFRONTIER = (
    (".gts", "OPX", "DEV", ".cgs"),
    (".cgs", "DEV", "USR", ".toml"),
    (".toml", "USR", "PUB", ".omniscience"),
)

@dataclass(frozen=True)
class Packet:
    index: int
    payload: bytes  # four consecutive 256-bit words, in row-major order
    zeros: int
    cumulative_zeros: int
    last_nibble: int
    last_nibble_bit_offset: int
    emitted_nibble_reports: int
    leaf_hash: bytes


def sample_matrix() -> bytes:
    """Stable synthetic matrix. Not a secret, GLYPH, real GTS or external proof."""
    return b"".join(hashlib.sha256(b"CGS-POEX-demo/row/" + i.to_bytes(2, "big")).digest()
                    for i in range(ROWS))


def split_packets(matrix: bytes) -> list[bytes]:
    if len(matrix) != ROWS * BYTES_PER_ROW:
        raise ValueError(f"expected {ROWS * BYTES_PER_ROW} bytes (256x256 bits); got {len(matrix)}")
    return [matrix[i:i + BYTES_PER_PACKET] for i in range(0, len(matrix), BYTES_PER_PACKET)]


def nibbles(payload: bytes) -> Iterator[int]:
    for byte in payload:
        yield byte >> 4
        yield byte & 0x0F


def sha256(blob: bytes) -> bytes:
    return hashlib.sha256(blob).digest()


def leaf_digest(index: int, payload: bytes) -> bytes:
    if not (0 <= index < PACKETS) or len(payload) != BYTES_PER_PACKET:
        raise ValueError("invalid POEX packet index/payload")
    return sha256(b"CGS-POEX/0.0.0/leaf\x00" + index.to_bytes(2, "big") + payload)


def parent_digest(left: bytes, right: bytes) -> bytes:
    return sha256(b"CGS-POEX/0.0.0/node\x00" + left + right)


def merkle_root(leaves: list[bytes]) -> bytes:
    if len(leaves) != PACKETS or any(len(x) != 32 for x in leaves):
        raise ValueError("expected exactly 64 sha256 packet leaves")
    level = leaves[:]
    while len(level) > 1:
        level = [parent_digest(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_branch(leaves: list[bytes], index: int) -> tuple[bytes, ...]:
    if len(leaves) != PACKETS or not 0 <= index < PACKETS:
        raise ValueError("invalid proof request")
    branch = []
    level, cursor = leaves[:], index
    while len(level) > 1:
        branch.append(level[cursor ^ 1])
        level = [parent_digest(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        cursor //= 2
    return tuple(branch)


def verify_branch(leaf: bytes, index: int, siblings: tuple[bytes, ...], root: bytes) -> bool:
    if not 0 <= index < PACKETS or len(siblings) != 6:
        return False
    acc, cursor = leaf, index
    for sibling in siblings:
        acc = parent_digest(acc, sibling) if cursor % 2 == 0 else parent_digest(sibling, acc)
        cursor //= 2
    return acc == root


def sequence(matrix: bytes) -> tuple[list[Packet], bytes]:
    blocks = split_packets(matrix)
    packets = []
    cumulative = 0
    for i, payload in enumerate(blocks):
        # .poe: invariant 4-bit internal zero counter; emits a report per quartet.
        count, reports, last = 0, 0, None
        for nibble in nibbles(payload):
            count += BITS_PER_NIBBLE - nibble.bit_count()
            reports += 1
            last = nibble
        cumulative += count
        packets.append(Packet(i, payload, count, cumulative, last,
                              i * BYTES_PER_PACKET * 8 + BYTES_PER_PACKET * 8 - 4,
                              reports, leaf_digest(i, payload)))
    assert b"".join(packet.payload for packet in packets) == matrix
    assert len(packets) == PACKETS
    return packets, merkle_root([p.leaf_hash for p in packets])


def public_candidate(packets: list[Packet], root: bytes) -> dict:
    """Only a non-anchored public CANDIDATE; does not reveal raw payload/mount."""
    return {
        "system": SYSTEM,
        "schema": VERSION,
        "source": "SYNTHETIC_SIMULATION",
        "status": "NOT_PUBLISHED",
        "poex_verified": False,
        "public_space": ".omniscience",
        "dimensions_bits": [ROWS, BITS_PER_ROW],
        "packet_shape_bits": [ROWS_PER_PACKET, BITS_PER_ROW],
        "packet_count": len(packets),
        "nibble_reports": sum(p.emitted_nibble_reports for p in packets),
        "candidate_poex_merkle_root_sha256": root.hex(),
        "gts_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="raw 8192-byte 256x256-bit matrix; default: deterministic synthetic matrix")
    parser.add_argument("--output", type=Path, default=Path("poex_public_candidate.json"), help="simulation manifest path")
    args = parser.parse_args()
    require_pixi()
    data = args.input.read_bytes() if args.input else sample_matrix()
    packets, root = sequence(data)
    manifest = public_candidate(packets, root)
    if args.input is not None:
        manifest["source"] = "USER_SUPPLIED_RAW_MATRIX"
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "matrix_bits": len(data) * 8,
        "packets": len(packets),
        "bits_per_packet": len(packets[0].payload) * 8,
        "nibble_reports": sum(p.emitted_nibble_reports for p in packets),
        "total_zeros": packets[-1].cumulative_zeros,
        "last_nibble_bit_offset": packets[-1].last_nibble_bit_offset,
        "last_nibble_value": packets[-1].last_nibble,
        "root_sha256": root.hex(),
        "inclusion_proof_packet_0_valid": verify_branch(packets[0].leaf_hash, 0,
               merkle_branch([p.leaf_hash for p in packets], 0), root),
        "published": False,
        "manifest": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()

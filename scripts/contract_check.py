#!/usr/bin/env python3
"""Offline contract validator for atCGS (ComplexGraphSync SemVer), not a deployed gate."""

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atcgs import SYSTEM, __version__, require_pixi  # noqa: E402  # single SemVer source of truth

SPEC = ROOT / "spec/contracts.toml"
FIXTURES = {
    "boot": {
        "identity": ("atCGS", "ALPHA", "BIOS", "ComplexGitSync", "M.m.p"),
        "current": (
            ("ComplexGitSync", "G", "POEX", ".gts"),
            (".gts", "G", "OPX", "TWX"),
            ("TWX", "ENV", "HWX", "DEV"),
            ("DEV", "HWX", "TWX", "USR"),
            ("USR", "TWX", "G", ".cgs"),
        ),
    },
    "bios_history": {
        "sequence": (
            ("BIOS", "ENV", "HWX", "TWX"),
            ("BOOT", "TWX", "POEX", "CGS"),
            ("CGS", "POEX", "TWX", "GTS"),
            ("GTS", "TWX", "OPX", "DEV"),
            ("DEV", "HWX", "ENV", "USR"),
            ("USR", "TWX", "GTS", "TWX"),
            ("OPX", "HWX", "ENV", "TWX"),
        ),
        "extensions": (("*G", "XGTS", "GX4G", "TWX"), ("CGS-ALPHA", "GX4G", "CGS", "TWX")),
    },
    "delta_nabla": {
        "sequence": (
            ("DELTA", "POEX", "NABLA", "OPX"),
            ("OPX", "ENV", "PRIME", "DELTA"),
            ("DELTA", "ENV", "PRIME", "NABLA"),
            ("NABLA", "EDGE", "POEX", "OPX"),
        )
    },
    "opfrontier": {
        "sequence": (
            (".gts", "OPX", "DEV", ".cgs"),
            (".cgs", "DEV", "USR", ".toml"),
            (".toml", "USR", "PUB", ".omniscience"),
        )
    },
    "public_boundary": {
        "sequence": (
            ("README", "atCGS", "USR", "PUB"),
            ("GLYPH", "POEX", "PUB", "DELTA"),
            ("DELTA", "POEX", "OPX", "HASH"),
            ("HASH", "DELTA", "CGS", "OPX"),
            (".cgs", "USR", "PUB", ".toml"),
        )
    },
    "key": {
        "prototype": (
            ("PUB", "DELTA", "POEX", "KEY"),
            ("KEY", "OPX", "CGS", "PUB"),
        )
    },
    "glyph": {
        "sequence": (
            ("NAME", "GLYPH", "POEX", "OPX"),
            ("NAME", "GLYPH", "PUB", ".toml"),
        )
    },
}
FRONTIERS = (
    (".poe", (".omniscience", ".cgs", "*G")),
    (".opx", (".cgitsync", ".omniscience", ".gts")),
)


def demand(ok, reason):
    if not ok:
        raise ValueError(reason)


def inspect(path=SPEC):
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    c = data["contract"]
    demand(c["version"] == __version__, f"contract version {c['version']!r} != {__version__!r}")
    demand(c["prime_g"] == ["NAME", "NODE", "EDGE", "OP"], "incorrect PRIME G")
    demand(c["prime_cgs"] == ["OPX", "DEV", "USR", "PUB"], "incorrect PRIME CGS")
    demand(
        c["public"] == ".omniscience"
        and c["private"] == ".cgitsync"
        and "internal" not in c,
        "incorrect system spaces",
    )
    for section, group in FIXTURES.items():
        for label, expected in group.items():
            actual = (
                tuple(tuple(x) for x in data[section][label])
                if label != "identity"
                else tuple(data[section][label])
            )
            demand(actual == expected, f"noncanonical {section}.{label}")
    demand(
        tuple((k, tuple(x)) for k, x in data["frontiers"].items()) == FRONTIERS,
        "noncanonical frontiers",
    )
    k = data["key"]
    demand(
        k["holder"] == "POEX" and k["definition"] == "sha256(GLYPH)",
        "KEY must be sha256(GLYPH), held by POEX",
    )
    v = data["poex"]
    demand(v["shape"] == [256, 256] and v["packet_shape"] == [4, 256], "incorrect matrix")
    demand(
        v["packets"] == 64 and v["packet_bytes"] == 128 and v["quartet_reports"] == 16384,
        "incorrect frames",
    )
    demand(v["published"] is False, "fixture must remain NOT_PUBLISHED")
    return {
        "status": "VALIDATED_SYNTAX",
        "version": c["version"],
        "bios_new_rows": 5,
        "bios_history_rows": 7,
        "history_extended_rows": 2,
        "delta_nabla_rows": 4,
        "opfrontier_rows": 3,
        "frontier_rows": 2,
        "public_rows": 5,
        "key_rows": 2,
        "glyph_rows": 2,
        "poex_verified": False,
        "published": False,
    }


def candidate(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    for key, expected in [
        ("system", SYSTEM),
        ("dimensions_bits", [256, 256]),
        ("packet_shape_bits", [4, 256]),
        ("packet_count", 64),
        ("nibble_reports", 16384),
        ("status", "NOT_PUBLISHED"),
        ("poex_verified", False),
        ("gts_verified", False),
        ("public_space", ".omniscience"),
    ]:
        demand(d.get(key) == expected, f"candidate {key} mismatch")
    root = d.get("candidate_poex_merkle_root_sha256")
    demand(
        isinstance(root, str) and len(root) == 64 and all(c in "0123456789abcdef" for c in root),
        "invalid root encoding",
    )
    demand(
        not any(
            k in d for k in ("payload", "private_path", "private_repo", "credentials", "secret")
        ),
        "private payload present",
    )
    return {
        "candidate": "ACCEPTED_OFFLINE_ONLY",
        "status": d["status"],
        "poex_verified": False,
        "published": False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("operation", choices=("inspect", "candidate"))
    ap.add_argument("file", nargs="?", type=Path)
    a = ap.parse_args()
    try:
        require_pixi()
        result = (
            inspect(a.file or SPEC)
            if a.operation == "inspect"
            else candidate(a.file or Path("candidate.json"))
        )
    except (ValueError, KeyError, FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(f"CONTRACT_REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

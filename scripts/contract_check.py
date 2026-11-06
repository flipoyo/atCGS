#!/usr/bin/env python3
"""Offline contract validator for atCGS (ComplexGraphSync SemVer), not a deployed gate."""

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atcgs import __version__, glyph, identity, pin, require_pixi  # noqa: E402  # single SemVer source of truth
from atcgs.commands import ROLE_CODES  # noqa: E402
from atcgs.journal import ROLES  # noqa: E402

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
    demand("holder" not in data["key"] and "definition" not in data["key"],
           "KEY no longer hashes a GLYPH (REFERENCE.md § 6)")
    check_glyph(data["glyph"])
    check_identity(data["identity"])
    return {
        "status": "VALIDATED_SYNTAX",
        "version": c["version"],
        "bios_new_rows": 5,
        "bios_history_rows": 7,
        "history_extended_rows": 2,
        "delta_nabla_rows": 4,
        "opfrontier_rows": 3,
        "frontier_rows": 2,
        "public_rows": 4,
        "key_rows": 2,
        "glyph_rows": 2,
        "opx_pinned": pin.read(path.parent.parent if path.parent.name == "spec" else path.parent) is not None,
        "published": False,
    }


def check_glyph(g):
    """The [glyph] envelope must be the one atcgs.glyph seals."""
    sizes = [len(glyph.MAGIC), 1, glyph.NONCE, glyph.PLAINTEXT, glyph.TAG]
    demand(g["shape"] == [glyph.SIDE, glyph.SIDE] and g["bytes"] == glyph.GLYPH_BYTES, "incorrect GLYPH size")
    demand(g["sizes"] == sizes and sum(sizes) == glyph.GLYPH_BYTES, "incorrect GLYPH layout")
    demand(g["layout"][0] == glyph.MAGIC.decode() and g["aead"] == "ChaCha20-Poly1305", "incorrect GLYPH seal")
    demand(g["growth"] == glyph.GROWTH and glyph.glyph_bytes(1) == glyph.GROWTH * glyph.GLYPH_BYTES, "incorrect GLYPH growth")
    demand(g["published"] is False, "a GLYPH is never published")


def check_identity(i):
    """The [identity] section must match atcgs.identity and atcgs.commands."""
    memory, iterations, lanes = identity.KDF_PROFILES["real"]
    demand(i["kdf"] == "Argon2id" and i["signature"] == "Ed25519", "incorrect identity primitives")
    demand(i["kdf_cost"] == {"memory_kib": memory, "iterations": iterations, "lanes": lanes},
           "incorrect Argon2id cost")
    demand(i["uid"] == "sha256(IDPUB)", "UID must be sha256(IDPUB)")
    demand(tuple(i["roles"]) == ROLES and i["codes"] == dict(ROLE_CODES), "incorrect roles or codes")
    demand(i["journals"] == ["identity.jsonl", "access.jsonl"], "incorrect journals")
    demand("opx_pub" not in i, "the OPX key is pinned in spec/opx.toml, not in contracts.toml")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("operation", choices=("inspect",))
    ap.add_argument("file", nargs="?", type=Path)
    a = ap.parse_args()
    try:
        require_pixi()
        result = inspect(a.file or SPEC)
    except (ValueError, KeyError, FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(f"CONTRACT_REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

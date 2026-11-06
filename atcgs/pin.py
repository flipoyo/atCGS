"""The OPX pin: the one public key every register is checked against (spec/opx.toml).

    # atCGS OPX: the key every register trusts. Written by `@cgs OPX init`; never edited by hand.
    [[pin]]
    opx_pub = "qL1FhYN4yQrRd6/cOa92zPG6rsu2t8JXirlntzsYDMo="
    uid     = "35c65c668cb895b0fff2e5ca094bbc465ee27f5cf43159a6ca72f33ed161d104"
    since   = 2026-11-05

The file is written by appending only: the last `[[pin]]` is the key in force, the earlier ones stay as history.
A pin made before this file existed, `spec/contracts.toml [identity] opx_pub`, is still read when there is none.
The pin cannot be a line of the register: the register is verified against it.
"""

from __future__ import annotations

import base64
import datetime
import tomllib
from pathlib import Path

PIN_FILE = Path("spec") / "opx.toml"
LEGACY_FILE = Path("spec") / "contracts.toml"
HEADER = """\
# atCGS OPX: the key every register trusts. Written by `@cgs OPX init`; never edited by hand.
# Append-only: the last [[pin]] is in force, the earlier ones are history.
"""


def _decode(text: str) -> bytes:
    pub = base64.b64decode(text, validate=True)
    if len(pub) != 32:
        raise ValueError("the pinned OPX key is not a 32-byte Ed25519 key")
    return pub


def history(root: Path) -> list[dict[str, object]]:
    """Every [[pin]] of *root*/spec/opx.toml, oldest first; empty when there is no such file."""
    path = Path(root) / PIN_FILE
    if not path.is_file():
        return []
    return list(tomllib.loads(path.read_text(encoding="utf-8")).get("pin", []))


def read(root: Path) -> bytes | None:
    """The key in force: the last [[pin]], else the legacy `contracts.toml` line, else None."""
    pins = history(root)
    if pins:
        return _decode(str(pins[-1]["opx_pub"]))
    legacy = Path(root) / LEGACY_FILE
    if legacy.is_file():
        text = tomllib.loads(legacy.read_text(encoding="utf-8")).get("identity", {}).get("opx_pub", "")
        return _decode(text) if text else None
    return None


def append(root: Path, pub: bytes, uid: str, when: datetime.date | None = None) -> bool:
    """Pin *pub*: append a [[pin]] unless it is already the key in force. Returns whether it wrote.

    Nothing is ever rewritten. A different key is appended after the older one(s), which stay as history.
    """
    if read(root) == pub:
        return False
    path = Path(root) / PIN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    block = (f'\n[[pin]]\nopx_pub = "{base64.b64encode(pub).decode()}"\nuid     = "{uid}"\n'
             f"since   = {(when or datetime.date.today()).isoformat()}\n")
    with path.open("a", encoding="utf-8") as handle:
        if path.stat().st_size == 0:
            handle.write(HEADER)
        handle.write(block)
    return True

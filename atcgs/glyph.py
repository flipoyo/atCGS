"""The GLYPH, the cover of a user's ssh keys (REFERENCE.md § 6).

    GLYPH = "CGSG" | version (1) | nonce (12) | ChaCha20-Poly1305(key, plaintext) | tag (16)
          = 4 + 1 + 12 + 8 159 + 16 = 8 192 bytes = 256 x 256 bits           (level 0)

The size grows by a factor 4 when the keys no longer fit: level 1 is 32 KiB (512 x 512 bits), level 2 is
128 KiB (1024 x 1024). The format is the same at every level; the level is read from the file length. A GLYPH
never shrinks, and its size tells the level, never the number of keys.

The key is HKDF(IDSEED), so only the user's login and password open it. The
plaintext is a length-prefixed JSON list of (repo, role, OpenSSH private key),
zero-padded to a fixed size: the GLYPH never tells how many keys it holds.
"""

from __future__ import annotations

import json
import os
import struct
from dataclasses import dataclass
from typing import Iterable, Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_ssh_private_key,
)

from atcgs.identity import Identity

SIDE = 256  # level 0
GLYPH_BYTES = SIDE * SIDE // 8  # 8 192
GROWTH = 4  # each level holds 4 times as many bytes as the one before
MAX_LEVEL = 4  # 2 MiB: about 4 500 keys
MAGIC, VERSION = b"CGSG", 1
NONCE, TAG = 12, 16
HEADER = len(MAGIC) + 1 + NONCE  # 17
PLAINTEXT = GLYPH_BYTES - HEADER - TAG  # 8 159, level 0
_LENGTH = struct.Struct(">I")


def glyph_bytes(level: int = 0) -> int:
    return GLYPH_BYTES * GROWTH**level


def plaintext_bytes(level: int = 0) -> int:
    return glyph_bytes(level) - HEADER - TAG


def side(level: int = 0) -> int:
    return SIDE * 2**level


def level_of(glyph: bytes) -> int:
    """The level a GLYPH's length names; GlyphError for any other length."""
    for level in range(MAX_LEVEL + 1):
        if len(glyph) == glyph_bytes(level):
            return level
    raise GlyphError("not a GLYPH: wrong size, magic or version")


class GlyphError(ValueError):
    """The GLYPH does not open, or the keys do not fit in it."""


@dataclass(frozen=True, slots=True, repr=False)
class SshKey:
    """One ssh key of the bundle: the private half lives only in memory."""

    repo: str
    role: str
    private: str  # OpenSSH private key, unencrypted, in memory only

    @classmethod
    def generate(cls, repo: str, role: str) -> SshKey:
        pem = Ed25519PrivateKey.generate().private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
        return cls(repo, role, pem.decode())

    @property
    def public(self) -> str:
        key = load_ssh_private_key(self.private.encode(), password=None)
        return key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()

    def __repr__(self) -> str:
        return f"SshKey(repo={self.repo!r}, role={self.role!r})"


def _payload(keys: Sequence[SshKey]) -> bytes:
    return json.dumps([{"repo": k.repo, "role": k.role, "private": k.private} for k in keys]).encode()


def usage(keys: Sequence[SshKey], level: int = 0) -> tuple[int, int]:
    """(bytes used, bytes available at the level the keys need, at least *level*): how full a GLYPH is."""
    used = _LENGTH.size + len(_payload(keys))
    level = max(level, _fit(used))
    return used, plaintext_bytes(level)


def _fit(used: int) -> int:
    """The smallest level whose plaintext holds *used* bytes."""
    for level in range(MAX_LEVEL + 1):
        if used <= plaintext_bytes(level):
            return level
    raise GlyphError(f"these ssh keys do not fit in a GLYPH, even at level {MAX_LEVEL}")


def seal(identity: Identity, keys: Sequence[SshKey], min_level: int = 0) -> bytes:
    """Seal the ssh keys into a fresh GLYPH; a new nonce each time.

    The GLYPH has the smallest level the keys fit in, and never less than *min_level*: it grows, it does not shrink.
    """
    payload = _payload(keys)
    level = max(min_level, _fit(_LENGTH.size + len(payload)))
    size = plaintext_bytes(level)
    plaintext = _LENGTH.pack(len(payload)) + payload
    plaintext += bytes(size - len(plaintext))
    nonce = os.urandom(NONCE)
    header = MAGIC + bytes([VERSION]) + nonce
    glyph = header + ChaCha20Poly1305(identity.glyph_key()).encrypt(nonce, plaintext, header)
    assert len(glyph) == glyph_bytes(level)
    return glyph


def open_glyph(identity: Identity, glyph: bytes) -> list[SshKey]:
    """Open a GLYPH; a wrong login/password or a single changed bit is refused."""
    level_of(glyph)  # any level is accepted; the length names it
    if glyph[:4] != MAGIC or glyph[4] != VERSION:
        raise GlyphError("not a GLYPH: wrong size, magic or version")
    header, nonce = glyph[:HEADER], glyph[5:HEADER]
    try:
        plaintext = ChaCha20Poly1305(identity.glyph_key()).decrypt(nonce, glyph[HEADER:], header)
    except InvalidTag:
        raise GlyphError("the GLYPH does not open: wrong login/password, or the GLYPH was altered") from None
    (length,) = _LENGTH.unpack_from(plaintext)
    return [SshKey(e["repo"], e["role"], e["private"]) for e in json.loads(plaintext[4:4 + length])]


def reseal(identity: Identity, glyph: bytes | None, added: Iterable[SshKey]) -> bytes:
    """Add keys to an existing GLYPH (or start one) and seal it again."""
    keys = open_glyph(identity, glyph) if glyph else []
    return seal(identity, [*keys, *added], min_level=level_of(glyph) if glyph else 0)


def to_pbm(glyph: bytes) -> bytes:
    """The GLYPH as a 256x256 1-bit image (binary PBM), to look at: it is noise."""
    edge = side(level_of(glyph))
    return f"P4\n{edge} {edge}\n".encode() + glyph

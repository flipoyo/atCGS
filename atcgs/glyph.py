"""The GLYPH, the cover of a user's ssh keys (REFERENCE.md § 6).

    GLYPH = "CGSG" | version (1) | nonce (12) | ChaCha20-Poly1305(key, plaintext) | tag (16)
          = 4 + 1 + 12 + 8 159 + 16 = 8 192 bytes = 256 x 256 bits

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

SIDE = 256
GLYPH_BYTES = SIDE * SIDE // 8  # 8 192
MAGIC, VERSION = b"CGSG", 1
NONCE, TAG = 12, 16
HEADER = len(MAGIC) + 1 + NONCE  # 17
PLAINTEXT = GLYPH_BYTES - HEADER - TAG  # 8 159
_LENGTH = struct.Struct(">I")


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


def seal(identity: Identity, keys: Sequence[SshKey]) -> bytes:
    """Seal the ssh keys into a fresh GLYPH; a new nonce each time."""
    payload = json.dumps([{"repo": k.repo, "role": k.role, "private": k.private} for k in keys]).encode()
    if _LENGTH.size + len(payload) > PLAINTEXT:
        raise GlyphError(f"{len(keys)} ssh keys do not fit in one GLYPH ({PLAINTEXT} bytes)")
    plaintext = _LENGTH.pack(len(payload)) + payload
    plaintext += bytes(PLAINTEXT - len(plaintext))
    nonce = os.urandom(NONCE)
    header = MAGIC + bytes([VERSION]) + nonce
    glyph = header + ChaCha20Poly1305(identity.glyph_key()).encrypt(nonce, plaintext, header)
    assert len(glyph) == GLYPH_BYTES
    return glyph


def open_glyph(identity: Identity, glyph: bytes) -> list[SshKey]:
    """Open a GLYPH; a wrong login/password or a single changed bit is refused."""
    if len(glyph) != GLYPH_BYTES or glyph[:4] != MAGIC or glyph[4] != VERSION:
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
    return seal(identity, [*keys, *added])


def to_pbm(glyph: bytes) -> bytes:
    """The GLYPH as a 256x256 1-bit image (binary PBM), to look at: it is noise."""
    if len(glyph) != GLYPH_BYTES:
        raise GlyphError("not a GLYPH")
    return f"P4\n{SIDE} {SIDE}\n".encode() + glyph

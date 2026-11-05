"""Identity key: login, password -> Ed25519 key pair (REFERENCE.md § 6).

Nothing here is stored. The same login and password always give the same key,
so the system never needs to look a login up: the client recomputes the UID and
finds it in the identity journal. The login is the salt, never a record.

Python cannot promise that a secret is wiped from memory. The seed is kept in
one object, never logged or printed, and dropped when the session ends.
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from dataclasses import dataclass, field
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Argon2id cost per profile: (memory in KiB, iterations, lanes).
# `real` is the README value; `test` is for CI only. The profile name is part of
# the salt, so a test key can never equal a real one.
KDF_PROFILES: Mapping[str, tuple[int, int, int]] = {
    "real": (256 * 1024, 3, 1),
    "test": (8 * 1024, 1, 1),
}
PROFILE_ENV = "ATCGS_KDF_PROFILE"
SALT_PREFIX = "atCGS/id/v1/"
GLYPH_INFO = b"atCGS/glyph/v1"


def profile_from_env(env: Mapping[str, str] | None = None) -> str:
    profile = (os.environ if env is None else env).get(PROFILE_ENV, "real")
    if profile not in KDF_PROFILES:
        raise ValueError(f"{PROFILE_ENV} must be one of {sorted(KDF_PROFILES)}")
    return profile


def uid_of(pub: bytes) -> str:
    """UID = sha256(IDPUB): the only name the system gives a user."""
    if len(pub) != 32:
        raise ValueError("an IDPUB is 32 bytes")
    return hashlib.sha256(pub).hexdigest()


def verify(pub: bytes, signature: bytes, data: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(signature, data)
    except (InvalidSignature, ValueError):
        return False
    return True


@dataclass(frozen=True, slots=True, repr=False)
class Identity:
    """IDSK, IDPUB and UID of one user, rebuilt at each login."""

    _seed: bytes = field(compare=False)
    pub: bytes

    @classmethod
    def from_seed(cls, seed: bytes) -> Identity:
        if len(seed) != 32:
            raise ValueError("an IDSEED is 32 bytes")
        key = Ed25519PrivateKey.from_private_bytes(seed)
        return cls(seed, key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))

    @property
    def uid(self) -> str:
        return uid_of(self.pub)

    def sign(self, data: bytes) -> bytes:
        return Ed25519PrivateKey.from_private_bytes(self._seed).sign(data)

    def glyph_key(self) -> bytes:
        """The 32-byte key that seals and opens this user's GLYPH."""
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=GLYPH_INFO).derive(self._seed)

    def __repr__(self) -> str:
        return f"Identity(uid={self.uid})"


def _normalise(text: str, what: str) -> bytes:
    if not text:
        raise ValueError(f"empty {what}")
    return unicodedata.normalize("NFC", text).encode("utf-8")


def derive(login: str, password: str, profile: str | None = None) -> Identity:
    """REFERENCE.md § 6: IDSEED = Argon2id(password, salt = prefix || profile || login)."""
    profile = profile or profile_from_env()
    if profile not in KDF_PROFILES:
        raise ValueError(f"unknown KDF profile: {profile!r}")
    memory, iterations, lanes = KDF_PROFILES[profile]
    salt = SALT_PREFIX.encode() + profile.encode() + b"/" + _normalise(login, "login")
    seed = Argon2id(salt=salt, length=32, iterations=iterations, lanes=lanes,
                    memory_cost=memory).derive(_normalise(password, "password"))
    return Identity.from_seed(seed)

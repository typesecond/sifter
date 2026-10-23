"""Search primitives. No network connections and no secret logging.

MIT licensed. See the retained notices in LICENSE.
"""
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import secrets
from typing import Optional

from eth_account import Account
from eth_keys.constants import SECPK1_N


@dataclass(frozen=True)
class Pattern:
    prefix: str = ""
    suffix: str = ""

    def __post_init__(self):
        for side in ("prefix", "suffix"):
            value = getattr(self, side).strip().lower()
            if value.startswith("0x"):
                value = value[2:]
            if not re.fullmatch(r"[0-9a-f]*", value):
                raise ValueError("Use hexadecimal characters: 0–9 and A–F.")
            object.__setattr__(self, side, value)
        if not self.prefix and not self.suffix:
            raise ValueError("Enter a prefix, suffix, or both.")
        if self.digits > 40:
            raise ValueError("Prefix and suffix must total at most 40 characters.")

    @property
    def digits(self):
        return len(self.prefix) + len(self.suffix)

    @property
    def expected_attempts(self):
        return 16 ** self.digits

    @property
    def mask(self):
        return self.prefix + "X" * (40 - self.digits) + self.suffix

    def matches(self, address):
        value = address.removeprefix("0x").lower()
        return len(value) == 40 and value.startswith(self.prefix) and value.endswith(self.suffix)

    def seconds_for(self, probability, rate):
        if not 0 < probability < 1 or rate <= 0:
            return math.inf
        # log1p retains precision for long, difficult patterns.
        return math.log1p(-probability) / math.log1p(-1 / self.expected_attempts) / rate


@dataclass(frozen=True)
class Result:
    address: str
    private_key: bytes = field(repr=False)

    @classmethod
    def from_key(cls, key):
        account = Account.from_key(key)
        return cls(account.address, bytes(account.key))


@dataclass(frozen=True)
class Event:
    kind: str
    message: str = ""
    rate: float = 0
    attempts: Optional[int] = None
    elapsed: float = 0
    result: Optional[Result] = field(default=None, repr=False)


def new_key():
    return (secrets.randbelow(SECPK1_N - 1) + 1).to_bytes(32, "big")


def combine_keys(seed, offset):
    """Add secret scalars modulo the curve ORDER, not the field prime."""
    scalar = (int.from_bytes(seed, "big") + int(offset, 16)) % SECPK1_N
    if scalar == 0:
        raise ValueError("The engine returned the zero private scalar.")
    return scalar.to_bytes(32, "big")


def export_keystore(result, password, destination):
    if not password:
        raise ValueError("A keystore password is required.")
    verified = Result.from_key(result.private_key)
    if verified.address.lower() != result.address.lower():
        raise ValueError("The address does not match its private key.")
    path = Path(destination).expanduser()
    # Use the library's standard scrypt parameters and a fresh salt/IV.
    document = Account.encrypt(result.private_key, password, kdf="scrypt")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path

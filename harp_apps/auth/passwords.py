"""Passwords: the policy they must meet, and how they are stored and checked.

Hashes are Argon2id PHC strings with the OWASP parameters (19 MiB, t=2, p=1). The policy follows NIST SP 800-63B-4:
15 to 256 characters, nothing from a bundled list of the most common passwords, no composition rule, no expiry.
"""

import asyncio
import unicodedata
from functools import cache
from importlib.resources import files

from argon2 import PasswordHasher as Argon2
from argon2 import Type
from argon2.exceptions import InvalidHashError, VerificationError

MIN_LENGTH = 15
MAX_LENGTH = 256

#: Argon2id, OWASP minimum configuration with 19 MiB of memory.
MEMORY_COST_KIB = 19456
TIME_COST = 2
PARALLELISM = 1

#: Verifications running at once: each one holds ``MEMORY_COST_KIB`` and a thread, an attacker must not exhaust either.
MAX_CONCURRENT = 4


class PasswordPolicyError(ValueError):
    """The password is refused; the message is safe to show to the person choosing it."""


@cache
def _common_passwords() -> frozenset[str]:
    text = files("harp_apps.auth").joinpath("data/common-passwords.txt").read_text(encoding="utf-8")
    return frozenset(line.strip().casefold() for line in text.splitlines() if line.strip())


def _normalize(password: str) -> str:
    # NFKC, so the same password typed on two keyboards is the same password
    return unicodedata.normalize("NFKC", password)


def check_policy(password: str) -> None:
    """Raises :class:`PasswordPolicyError` if the password may not be used."""
    password = _normalize(password)
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(f"The password must have at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(f"The password must have at most {MAX_LENGTH} characters.")
    if password.casefold() in _common_passwords():
        raise PasswordPolicyError("The password is too common, choose another one.")


class PasswordHasher:
    """Hashes and verifies passwords off the event loop, with a cap on how many run at once."""

    def __init__(self, *, max_concurrent: int = MAX_CONCURRENT):
        self._argon2 = Argon2(time_cost=TIME_COST, memory_cost=MEMORY_COST_KIB, parallelism=PARALLELISM, type=Type.ID)
        self._slots = asyncio.Semaphore(max_concurrent)
        self._dummy = self._argon2.hash("harp has no such account")

    async def hash(self, password: str) -> str:
        async with self._slots:
            return await asyncio.to_thread(self._argon2.hash, _normalize(password))

    def _verify_sync(self, password: str, stored: str) -> bool:
        try:
            return self._argon2.verify(stored, _normalize(password))
        except (VerificationError, InvalidHashError):
            return False

    async def verify(self, password: str, stored: str) -> bool:
        """Whether ``password`` is the one ``stored`` hashes. A malformed hash is a refusal, never an error."""
        async with self._slots:
            return await asyncio.to_thread(self._verify_sync, password, stored)

    async def verify_unknown(self, password: str) -> None:
        """Pays what a verification costs when there is nothing to verify against, so that an unknown account takes as
        long to refuse as a wrong password does."""
        await self.verify(password, self._dummy)

    def needs_rehash(self, stored: str) -> bool:
        """Whether ``stored`` was made with other parameters than the current ones."""
        try:
            return self._argon2.check_needs_rehash(stored)
        except InvalidHashError:
            return True

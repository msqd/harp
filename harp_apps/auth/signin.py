"""Signing in with a password, and changing it."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Optional

from harp_apps.auth.models import Account, AccountKind, IdentitiesRepository, Identity, Session
from harp_apps.auth.passwords import MAX_LENGTH, PasswordHasher, check_policy
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.throttle import SignInThrottle
from harp_apps.storage.types import IStorage

#: Longer than any password the policy accepts, by a margin: a refusal needs no hashing of megabytes.
MAX_PASSWORD_INPUT = 4 * MAX_LENGTH
MAX_USERNAME_INPUT = 255


@dataclass(frozen=True)
class Signed:
    """The password was right: a session is open. ``secret`` is for the cookie, nowhere else."""

    secret: str
    session: Session


@dataclass(frozen=True)
class Refused:
    """Unknown account, wrong password, disabled account, no password: the same answer for all of them."""


@dataclass(frozen=True)
class Throttled:
    """Too many failures: try again in ``retry_after`` seconds. The password was not looked at."""

    retry_after: float


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _usable(account: Account) -> bool:
    return account.disabled_at is None and account.kind != AccountKind.SYSTEM


class Authenticator:
    def __init__(
        self,
        identities: IdentitiesRepository,
        sessions: SessionsService,
        hasher: PasswordHasher,
        throttle: SignInThrottle,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ):
        self.identities = identities
        self.sessions = sessions
        self.hasher = hasher
        self.throttle = throttle
        self.clock = clock

    @classmethod
    def from_storage(
        cls, storage: IStorage, sessions: SessionsService, hasher: PasswordHasher, throttle: SignInThrottle
    ) -> "Authenticator":
        return cls(IdentitiesRepository(storage.accounts.session_factory), sessions, hasher, throttle)

    async def sign_in(
        self, username: str, password: str, *, ip: str, user_agent: Optional[str]
    ) -> Signed | Refused | Throttled:
        if (wait := self.throttle.retry_after(username, ip)) > 0:
            return Throttled(wait)
        # counted as a failure from the start and taken back on success: guesses sent at once all meet the wait
        self.throttle.failed(username, ip)

        found = await self._verified(username, password)
        if found is None:
            return Refused()
        identity, account = found

        self.throttle.succeeded(username, ip)
        await self._rehash_if_outdated(identity, password)
        await self.identities.signed_in(identity.id, self.clock())
        secret, session = await self.sessions.open(account.id, identity.id, user_agent=user_agent, ip=ip)
        return Signed(secret, session)

    async def _verified(self, username: str, password: str) -> Optional[tuple[Identity, Account]]:
        """The identity and account when the password is right and the account may sign in. A verification is paid in
        every case but absurd input, so the time taken tells nothing about which of them failed."""
        if not (0 < len(username) <= MAX_USERNAME_INPUT and 0 < len(password) <= MAX_PASSWORD_INPUT):
            return None
        found = await self.identities.find_password(username)
        if found is None or not found[0].password_hash:
            await self.hasher.verify_unknown(password)
            return None
        identity, account = found
        matches = await self.hasher.verify(password, identity.password_hash)
        return found if matches and _usable(account) else None

    async def _rehash_if_outdated(self, identity: Identity, password: str) -> None:
        if self.hasher.needs_rehash(identity.password_hash):
            await self.identities.set_password_hash(identity.id, await self.hasher.hash(password))

    async def change_password(
        self, account_id: int, username: str, current: str, new: str, *, keep: int, ip: str
    ) -> bool:
        """
        Replaces the password of the account and ends its other sessions, ``keep`` being the one that asks. Returns
        False when the current password is not the right one, or when guessing it was slowed down. Raises
        :class:`~harp_apps.auth.passwords.PasswordPolicyError` when the new one is refused.
        """
        if self.throttle.retry_after(username, ip) > 0:
            return False
        self.throttle.failed(username, ip)
        identity = await self.identities.find_password_of_account(account_id)
        if (
            identity is None
            or not identity.password_hash
            or not (0 < len(current) <= MAX_PASSWORD_INPUT)
            or not await self.hasher.verify(current, identity.password_hash)
        ):
            return False
        self.throttle.succeeded(username, ip)
        check_policy(new)
        await self.identities.set_password_hash(identity.id, await self.hasher.hash(new))
        await self.sessions.revoke_others(account_id, keep=keep)
        return True

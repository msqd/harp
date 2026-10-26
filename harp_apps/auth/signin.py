"""Signing in with a password, and changing it."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Optional

from harp_apps.auth.models import Account, AccountKind, IdentitiesRepository, Identity, Session, login_of
from harp_apps.auth.passwords import MAX_LENGTH, HasherBusy, PasswordHasher, check_policy
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.throttle import Admitted, Refused as ThrottleRefused, SignInThrottle
from harp_apps.storage.types import IStorage

#: Longer than any password the policy accepts, by a margin: a refusal needs no hashing of megabytes.
MAX_PASSWORD_INPUT = 4 * MAX_LENGTH

#: The throttle key of a name that cannot be a login at all, so that every such name shares one count.
INVALID_LOGIN = "\0invalid"


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
    """Too many failures from this address against this account: try again in ``retry_after`` seconds. The password was
    not looked at."""

    retry_after: float


@dataclass(frozen=True)
class Busy:
    """The hashing queue is full. Nothing was looked at or counted: try again in a moment."""

    retry_after: float = 1.0


@dataclass(frozen=True)
class Changed:
    """The password was replaced and the other sessions of the account are over."""


@dataclass(frozen=True)
class Checked:
    """The attempt went through the throttle and its check ran: ``value`` is what the check answered."""

    value: Any


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

    async def guarded(self, key: str, ip: str, check: Callable[[], Awaitable[Any]]) -> Checked | Throttled | Busy:
        """
        Runs ``check`` (does this person know the secret?) under the throttle, for a way in that has none of its own.
        It is refused (:class:`Throttled`) when a limit is over, without holding anything; a falsy answer counts as a
        failure, and so does a client that leaves or an error; a full hashing queue is :class:`Busy` and counts for
        nothing.
        """
        admitted = self.throttle.begin(key, ip)
        if isinstance(admitted, ThrottleRefused):
            return Throttled(admitted.retry_after)
        assert isinstance(admitted, Admitted)
        outcome = "failure"
        try:
            value = await check()
            outcome = "success" if value else "failure"
            return Checked(value)
        except HasherBusy:
            outcome = "abandoned"
            return Busy()
        finally:
            self.throttle.end(admitted, outcome)

    async def sign_in(
        self, username: str, password: str, *, ip: str, user_agent: Optional[str]
    ) -> Signed | Refused | Throttled | Busy:
        # case and accent variants of a name are one name, for the lookup and for the throttle
        login = login_of(username)
        checked = await self.guarded(login or INVALID_LOGIN, ip, lambda: self._verified(login, password))
        if not isinstance(checked, Checked):
            return checked
        if checked.value is None:
            return Refused()
        identity, account = checked.value

        await self._rehash_if_outdated(identity, password)
        await self.identities.signed_in(identity.id, self.clock())
        secret, session = await self.sessions.open(
            account.id, identity.id, user_agent=user_agent, ip=ip, credential_version=identity.password_version
        )
        return Signed(secret, session)

    async def _verified(self, login: Optional[str], password: str) -> Optional[tuple[Identity, Account]]:
        """The identity and account when the password is right and the account may sign in. A verification is paid in
        every case but an absurd password, so the time taken tells nothing about which of them failed."""
        if not 0 < len(password) <= MAX_PASSWORD_INPUT:
            return None
        found = await self.identities.find_password(login) if login else None
        if found is None or not found[0].password_hash:
            await self.hasher.verify_unknown(password)
            return None
        identity, account = found
        matches = await self.hasher.verify(password, identity.password_hash)
        return found if matches and _usable(account) else None

    async def _rehash_if_outdated(self, identity: Identity, password: str) -> None:
        if self.hasher.needs_rehash(identity.password_hash):
            await self.identities.set_password_hash(
                identity.id, await self.hasher.hash(password), replacing=identity.password_hash
            )

    async def change_password(
        self, account_id: int, username: str, current: str, new: str, *, keep: int, ip: str
    ) -> Changed | Refused | Throttled | Busy:
        """
        Replaces the password of the account and ends its other sessions (one transaction), ``keep`` being the one that
        asks. :class:`Refused` when the current password is not the right one, :class:`Throttled` when guessing it is
        over a limit, :class:`Busy` when the hashing queue is full. Raises :class:`~harp_apps.auth.passwords.PasswordPolicyError` when the new one is refused.
        """
        check_policy(new)
        identity = await self.identities.find_password_of_account(account_id)

        async def current_is_right() -> bool:
            if identity is None or not identity.password_hash or not 0 < len(current) <= MAX_PASSWORD_INPUT:
                return False
            return await self.hasher.verify(current, identity.password_hash)

        checked = await self.guarded(login_of(username) or INVALID_LOGIN, ip, current_is_right)
        if not isinstance(checked, Checked):
            return checked
        if not checked.value:
            return Refused()
        try:
            new_hash = await self.hasher.hash(new)
        except HasherBusy:
            return Busy()
        await self.identities.replace_password(identity.id, new_hash, account_id=account_id, keep=keep, at=self.clock())
        return Changed()

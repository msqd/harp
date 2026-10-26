"""Resolving a request to the actor it stands for."""

from datetime import UTC, datetime, timedelta
from typing import Callable, Optional

from sqlalchemy import update
from sqlalchemy.exc import NoResultFound

from harp.security.actor import Actor, ActorAccount, Role, effective_role
from harp_apps.auth.models import Account, AccountKind, AccountsRepository
from harp_apps.auth.sessions import SessionsService
from harp_apps.storage.types import IStorage

#: An account's ``last_seen_at`` is written at most this often.
LAST_SEEN_EVERY = timedelta(minutes=1)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ActorResolver:
    """
    Turns a credential already verified by a way in (Basic today, sessions and tokens later) into an
    :class:`~harp.security.actor.Actor`.

    This is the one place that reads the account (on every request, so a demotion or a disabled account applies at the
    next request) and the one place that applies the cap of the credential to its role.
    """

    def __init__(
        self,
        accounts: AccountsRepository,
        *,
        sessions: Optional[SessionsService] = None,
        clock: Callable[[], datetime] = _utcnow,
    ):
        self.accounts = accounts
        self.sessions = sessions
        self.clock = clock

    @classmethod
    def from_storage(cls, storage: IStorage, sessions: SessionsService) -> "ActorResolver":
        return cls(storage.accounts, sessions=sessions)

    async def resolve(
        self,
        username: str,
        *,
        via: str,
        via_id: Optional[str] = None,
        cap: Optional[Role] = None,
        client: Optional[str] = None,
    ) -> Optional[Actor]:
        """The actor of the account named ``username``, or None if nobody may act as it (unknown or disabled)."""
        try:
            account = await self.accounts.find_one({"username": username})
        except NoResultFound:
            return None
        return await self._actor(account, via=via, via_id=via_id, cap=cap, client=client)

    async def session(self, secret: str) -> Optional[Actor]:
        """The actor of the dashboard session the secret of the cookie opens, or None: unknown, revoked, ended by its
        idle time or its age, or of an account that may no longer act."""
        if self.sessions is None:
            return None
        row = await self.sessions.authenticate(secret)
        if row is None:
            return None
        try:
            account = await self.accounts.find_one({"id": row.account_id})
        except NoResultFound:
            return None
        return await self._actor(account, via="session", via_id=str(row.id))

    async def basic(self, username: str) -> Optional[Actor]:
        """
        The actor of a user of the configuration authenticated with Basic. Its account was created by the one-time
        import: without one (deleted, never imported) nobody acts.
        """
        return await self.resolve(username, via="basic")

    async def _actor(self, account: Account, *, via, via_id=None, cap=None, client=None) -> Optional[Actor]:
        if account.disabled_at is not None or account.kind == AccountKind.SYSTEM:
            return None
        await self._see(account)
        return Actor(
            account=ActorAccount(
                id=account.id, username=account.username, role=account.role, display_name=account.display_name
            ),
            role=effective_role(account.role, cap),
            via=via,
            via_id=via_id,
            client=client,
        )

    async def _see(self, account: Account) -> None:
        now = self.clock()
        if account.last_seen_at is not None and now - account.last_seen_at < LAST_SEEN_EVERY:
            return
        async with self.accounts.session_factory() as session:
            await session.execute(update(Account).where(Account.id == account.id).values(last_seen_at=now))
            await session.commit()

"""Dashboard sessions: server-side rows, a secret in the cookie.

The cookie carries a random secret and nothing else; the row holds its SHA-256, so a copy of the table gives nobody a
session. A 256 bits random secret needs no signature: there is nothing to forge, only something to guess.
"""

import re
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Callable, Optional

from harp_apps.auth.models import Session, SessionsRepository
from harp_apps.auth.settings import AuthSettings
from harp_apps.storage.types import IStorage

#: ``last_seen_at`` is written at most this often.
LAST_SEEN_EVERY = timedelta(minutes=1)

SECRET_BYTES = 32

#: What ``secrets.token_urlsafe(SECRET_BYTES)`` produces; anything else is not worth a lookup.
SECRET_SHAPE = re.compile(r"[A-Za-z0-9_-]{43}")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def hash_secret(secret: str) -> str:
    return sha256(secret.encode()).hexdigest()


class SessionsService:
    def __init__(
        self, sessions: SessionsRepository, settings: AuthSettings, *, clock: Callable[[], datetime] = _utcnow
    ):
        self.sessions = sessions
        self.settings = settings
        self.clock = clock

    @classmethod
    def from_storage(cls, storage: IStorage, settings: AuthSettings) -> "SessionsService":
        return cls(SessionsRepository(storage.accounts.session_factory), settings)

    async def open(
        self,
        account_id: int,
        identity_id: int,
        *,
        user_agent: Optional[str],
        ip: Optional[str],
        credential_version: int = 0,
    ):
        """Opens a session. Returns the secret for the cookie (it is not kept) and the row."""
        secret = secrets.token_urlsafe(SECRET_BYTES)
        now = self.clock()
        row = await self.sessions.create(
            {
                "secret_hash": hash_secret(secret),
                "account_id": account_id,
                "identity_id": identity_id,
                "credential_version": credential_version,
                "created_at": now,
                "last_seen_at": now,
                "expires_at": now + self.settings.session_max_age,
                "user_agent": user_agent[:512] if user_agent else None,
                "ip": ip[:45] if ip else None,
            }
        )
        return secret, row

    async def authenticate(self, secret: str) -> Optional[Session]:
        """The session this secret opens, or None when it is unknown, revoked, past its maximum age or idle for too
        long. Both limits are checked here, on the server, for every request."""
        if not SECRET_SHAPE.fullmatch(secret):
            return None
        row = await self.sessions.find_by_secret_hash(hash_secret(secret))
        if row is None:
            return None
        now = self.clock()
        if row.revoked_at is not None or now >= row.expires_at or now - row.last_seen_at >= self.settings.session_idle:
            return None
        if now - row.last_seen_at >= LAST_SEEN_EVERY:
            await self.sessions.seen(row.id, now)
        return row

    async def revoke(self, session_id: int) -> int:
        return await self.sessions.revoke(session_id, self.clock())

    async def revoke_all(self, account_id: int) -> int:
        return await self.sessions.revoke_all(account_id, self.clock())

    async def revoke_others(self, account_id: int, *, keep: int) -> int:
        return await self.sessions.revoke_others(account_id, keep, self.clock())

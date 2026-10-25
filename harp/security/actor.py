"""Who is acting, as a contract of the core.

Resolving a request yields one :class:`Actor`: the account, the role it acts with, how it got in (``via``, ``via_id``)
and, when something acts on its behalf, the client. The authentication application produces it. Controllers and role
checks read this and nothing else, so a new way in (session, token, ...) changes the resolver and no controller.

The effective role is ``min(account role, cap of the credential)``, computed once by :func:`effective_role`.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

ACTOR_EXTENSION = "actor"
"""Key of the request extension that holds the actor."""


class Role(IntEnum):
    """What an account may do. Ordered: each role includes everything the one below it may do."""

    VIEWER = 1
    EDITOR = 2
    ADMIN = 3

    @property
    def label(self) -> str:
        """Lower case name, as stored and as shown to the API clients."""
        return self.name.lower()

    @classmethod
    def parse(cls, label: str) -> "Role":
        try:
            return cls[label.upper()]
        except KeyError:
            raise ValueError(f"Unknown role {label!r}, expected one of: {', '.join(r.label for r in cls)}.") from None


def effective_role(account_role: Role, cap: Optional[Role] = None) -> Role:
    """The role a request acts with: the account's, lowered to the cap of the credential it came with (if any)."""
    return account_role if cap is None else min(account_role, cap)


@dataclass(frozen=True, slots=True)
class ActorAccount:
    """The account an actor stands for, as read when the request was resolved."""

    id: Optional[int]
    username: str
    role: Role
    display_name: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Actor:
    account: ActorAccount
    role: Role
    """Effective role."""
    via: str
    """How the request got in: ``basic``, later ``session``, ``token``."""
    via_id: Optional[str] = None
    """Identifies the credential among the account's (a session or token id)."""
    client: Optional[str] = None
    """What acts on behalf of the account, if anything."""

    def can(self, required: Role) -> bool:
        return self.role >= required


def get_actor(request) -> Optional[Actor]:
    return request.extensions.get(ACTOR_EXTENSION)


def set_actor(request, actor: Actor) -> None:
    request.extensions[ACTOR_EXTENSION] = actor

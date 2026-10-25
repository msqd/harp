"""
What an auditable event carries, for the audit application to record without the acting application knowing it.

An acting application declares its event with :func:`~harp.unit_of_work.auditable` and fills these fields; the audit
application reads them. Neither depends on the other, only on this contract.
"""

from dataclasses import dataclass
from typing import Any, Optional

from whistle import Event

__all__ = ["Actor", "AuditableEvent", "Target"]


@dataclass(frozen=True)
class Actor:
    """Who acts. ``via`` is one of ``session``, ``token``, ``cli`` or ``system`` (HARP acting on its own)."""

    account_id: Optional[int] = None
    #: Copied (the username), so the event stays readable once the account is gone.
    label: Optional[str] = None
    via: str = "system"
    via_id: Optional[int] = None
    client: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class Target:
    """What the action is about. The label is copied, so the event stays readable once the target is gone."""

    type: str
    id: Optional[int | str] = None
    label: Optional[str] = None


class AuditableEvent(Event):
    """Base for events declared ``auditable``. ``outcome`` is ``succeeded``, ``failed`` or ``denied``."""

    def __init__(
        self,
        *,
        actor: Optional[Actor] = None,
        target: Optional[Target] = None,
        outcome: str = "succeeded",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__()
        self.actor = actor or Actor()
        self.target = target
        self.outcome = outcome
        self.details = details or {}

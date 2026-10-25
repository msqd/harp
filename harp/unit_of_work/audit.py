"""
What an auditable event carries, for the audit application to record without the acting application knowing it.

An acting application declares its event with :func:`~harp.unit_of_work.auditable` and fills these fields; the audit
application reads them. Neither depends on the other, only on this contract.
"""

import re
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

from whistle import Event

__all__ = ["Actor", "AuditableEvent", "Target", "is_secret_field"]


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


_SECRET_FIELD = re.compile(r"pass|pwd|secret|token|key|auth|credential|cookie|recovery|otp|private|signature", re.I)
_IDENTIFIER_FIELD = re.compile(r"_(id|name|label|type|prefix)$", re.I)


def is_secret_field(name: str) -> bool:
    """Tell if a detail field name looks like it holds a secret (``token``, ``password``; not ``token_id``)."""
    return bool(_SECRET_FIELD.search(name)) and not _IDENTIFIER_FIELD.search(name)


class AuditableEvent(Event):
    """
    Base for events declared ``auditable``. ``outcome`` is ``succeeded``, ``failed`` or ``denied``.

    Default-deny on details: a subclass lists in ``details_fields`` the names it may put in ``details``, and only those
    are recorded and logged. An event gets no field for a secret (a token creation declares ``prefix`` and ``name``,
    never the token), and a class declaring a field named like a secret cannot be defined.
    """

    #: Names of the ``details`` this event may carry.
    details_fields: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        secret = [name for name in cls.details_fields if is_secret_field(name)]
        if secret:
            raise TypeError(f"{cls.__name__} declares detail fields that look like secrets: {', '.join(secret)}.")

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

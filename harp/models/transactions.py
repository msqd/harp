import dataclasses
from datetime import datetime
from typing import List

from .base import Entity
from .messages import Message


@dataclasses.dataclass(kw_only=True)
class Transaction(Entity):
    id: str = None
    """Unique identifier for this transaction."""

    type: str  # enum http websocket lifecycle ...
    """Type of ASGI transaction: http, websocket, lifecycle, ..."""

    endpoint: str = None
    """Endpoint name, if any (this describes which proxy controller handled the request)."""

    started_at: datetime
    """Timestamp of the transaction start."""

    finished_at: datetime = None
    """Timestamp of the transaction end (if it has ended), or None."""

    # Computed fields

    elapsed: float = None
    """Elapsed time in seconds, if the transaction has ended."""

    tpdex: int = None
    """TPDEX score, if the transaction has ended."""

    # Relations

    messages: List[Message] = None
    tags: dict = dataclasses.field(default_factory=dict)

    # Extra attributes

    extras: dict = dataclasses.field(default_factory=dict)

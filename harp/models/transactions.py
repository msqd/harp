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

    # Markers, used for transaction management (e.g. skip storage on high pressure)
    markers: set = dataclasses.field(default_factory=set)

    def as_storable_dict(self, /, *, with_messages=False, with_tags=False):
        """Create a dict that can be passed to a storage creation method."""
        data = self._asdict()

        if not with_messages:
            data.pop("messages", None)

        if not with_tags:
            data.pop("tags", None)

        extras = data.pop("extras", {})

        data["x_cached"] = extras.get("cached")
        data["x_method"] = extras.get("method")
        data["x_no_cache"] = bool(extras.get("no_cache"))
        data["x_status_class"] = extras.get("status_class")

        return data

    def _asdict(self, /, *, secure=True):
        result = dataclasses.asdict(self)
        del result["markers"]
        return result

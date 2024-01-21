import dataclasses
from datetime import datetime

from .base import Entity


@dataclasses.dataclass(kw_only=True)
class Message(Entity):
    id: int = None
    transaction_id: str
    kind: str
    summary: str
    headers: str
    body: str
    created_at: datetime = None

import dataclasses
from datetime import datetime
from typing import Any

from harp.core.models.base import Entity


@dataclasses.dataclass
class Message(Entity):
    type: str
    content: Any
    created_at: datetime = None

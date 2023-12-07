import dataclasses
from typing import Any

from harp.core.models.base import Entity


@dataclasses.dataclass
class Message(Entity):
    type: str
    content: Any

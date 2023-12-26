import dataclasses
import hashlib
import json
from datetime import datetime

from harp.core.models.base import Entity
from harp.utils.bytes import ensure_bytes, ensure_str


@dataclasses.dataclass(kw_only=True)
class Message(Entity):
    id: int = None
    transaction_id: str
    kind: str
    summary: str
    headers: str
    body: str
    created_at: datetime = None


@dataclasses.dataclass
class Blob(Entity):
    id: str
    data: bytes
    content_type: str = None

    @classmethod
    def from_data(cls, data, /, *, content_type=None):
        content_type = ensure_str(content_type) if content_type else None
        data = ensure_bytes(data)
        return cls(
            id=hashlib.sha1((content_type.encode("utf-8") if content_type else b"") + b"\n" + data).hexdigest(),
            data=data,
            content_type=content_type,
        )

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return True

    def prettify(self):
        if self.content_type == "application/json":
            return json.dumps(json.loads(self.data), indent=4)

        raise NotImplementedError(f"Cannot prettify blob of type {self.content_type}")

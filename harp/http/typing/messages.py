from datetime import UTC, datetime
from typing import Optional

from multidict import MultiDictProxy


class BaseMessage:
    protocol: str
    kind: str
    created_at: datetime

    def __init__(self, *, extensions: Optional[dict] = None):
        self.created_at = datetime.now(UTC)

        self._extensions = extensions or {}

    @property
    def extensions(self) -> dict:
        return self._extensions

    async def aread(self):
        pass


class BaseHttpMessage(BaseMessage):
    protocol = "http"

    @property
    def headers(self) -> MultiDictProxy:
        raise NotImplementedError

    @property
    def body(self) -> bytes:
        raise NotImplementedError

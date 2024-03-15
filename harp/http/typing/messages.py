from datetime import UTC, datetime

from multidict import MultiDictProxy


class BaseMessage:
    protocol: str
    kind: str
    created_at: datetime

    def __init__(self):
        self.created_at = datetime.now(UTC)

        self._context = {}

    @property
    def context(self) -> dict:
        return self._context

    async def join(self):
        pass


class BaseHttpMessage(BaseMessage):
    protocol = "http"

    @property
    def headers(self) -> MultiDictProxy:
        raise NotImplementedError

    @property
    def body(self) -> bytes:
        raise NotImplementedError

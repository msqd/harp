from datetime import UTC, datetime
from typing import Protocol

from multidict import CIMultiDict, MultiDict


class HttpRequestBridge(Protocol):
    def get_server_ipaddr(self) -> str:
        ...

    def get_server_port(self) -> int:
        ...

    def get_method(self) -> str:
        ...

    def get_path(self) -> str:
        ...

    def get_query(self) -> MultiDict:
        ...

    def get_headers(self) -> CIMultiDict:
        ...


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


class BaseHttpMessage(BaseMessage):
    protocol = "http"

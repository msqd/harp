from typing import Protocol


class MessageSerializer(Protocol):
    @property
    def summary(self) -> str:
        return ...

    @property
    def headers(self) -> str:
        return ...

    @property
    def body(self) -> bytes:
        return ...

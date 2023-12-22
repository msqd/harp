import datetime
from typing import Protocol


class Message(Protocol):
    @property
    def kind(self) -> str:
        """Message kind, used to describe the message within a transaction."""
        return ...

    @property
    def created_at(self) -> datetime.datetime:
        """Message creation timestamp."""
        return ...


class SerializableMessage(Protocol):
    @property
    def serialized_summary(self) -> str:
        """Message summary, as a string (todo: this is first implementation, we may want to do better)."""
        return ...

    @property
    def serialized_headers(self) -> str:
        """Message headers, as a string (todo: this is first implementation, we may want to do better)."""
        return ...

    @property
    def serialized_body(self) -> bytes:
        """Message body, as bytes (todo: this is first implementation, we may want to do better)."""
        return ...


class Contextualized(Protocol):
    @property
    def context(self) -> dict:
        """Contextual data for this message's lifecycle."""
        return ...

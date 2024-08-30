from typing import Self, Type

from pydantic import BaseModel, ConfigDict


class BaseConfigurable(BaseModel):
    """
    Base class for configurables (a.k.a settings definitions). For your settings definitions, prefer
    :class:`Configurable` over this base class (see below).

    Extends Pydantic's BaseModel.

    """

    @classmethod
    def from_dict(cls: Type[Self], data: dict) -> Self:
        """Construct a new instance from a dictionary."""
        return cls(**data)

    @classmethod
    def from_kwargs(cls: Type[Self], **kwargs) -> Self:
        """Construct a new instance from keyword arguments."""
        return cls(**kwargs)

    def __getitem__(self, item):
        """Allow access to nested values using dot notation."""
        value = self
        for bit in item.split("."):
            value = getattr(value, bit)
        return value


class Configurable(BaseConfigurable):
    """A settings definition base."""

    model_config = ConfigDict(extra="forbid")

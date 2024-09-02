from typing import Optional

from pydantic import ConfigDict, Field, model_serializer, model_validator

from .base import BaseConfigurable


class Service(BaseConfigurable):
    """A settings base class for service definitions."""

    model_config = ConfigDict(extra="allow")

    base: Optional[str] = None
    type: Optional[str] = None
    constructor: Optional[str] = None
    arguments: Optional[dict] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def __validate(cls, values):
        """Use extra fields as arguments."""
        arguments = values.get("arguments", {})
        for k in list(values.keys()):
            if k not in cls.model_fields:
                arguments[k] = values.pop(k)
        if len(arguments):
            return {**values, "arguments": arguments}
        return values

    @model_serializer(mode="wrap")
    def __serialize(self, wrapped, context):
        """Enhance serialization logic to inline arguments, unless they conflict with a model field."""
        data = wrapped(self, context)
        arguments = data.pop("arguments", {})
        inline_arguments = {}
        for k in list(arguments.keys()):
            if k not in self.model_fields:
                inline_arguments[k] = arguments.pop(k)

        for k in ("base", "type", "constructor"):
            if k in data and data[k] is None:
                data.pop(k)

        return {
            **data,
            **({"arguments": arguments} if len(arguments) else {}),
            **inline_arguments,
        }

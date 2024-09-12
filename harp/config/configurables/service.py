from typing import Optional

from pydantic import ConfigDict, Field, model_serializer, model_validator

from .base import BaseConfigurable


class Service(BaseConfigurable):
    """A settings base class for service definitions."""

    model_config = ConfigDict(extra="allow")

    #: Base type for service definition. This is not usually the base interface that the service implements, and you
    #: should use the `type` field to override the actually instanciated type.
    base: Optional[str] = Field(default=None, description="Base type for service definition.")

    #: Type for service definition. This is the actual type that will be instanciated.
    type: Optional[str] = Field(default=None, description="Type for service definition.")

    #: Constructor for service definition. If provided, will be used instead of the default constructor.
    constructor: Optional[str] = Field(default=None, description="Optional custom constructor for the service.")

    #: Arguments for the service constructor, by name.
    arguments: Optional[dict] = Field(default_factory=dict, description="Arguments for the service constructor.")

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

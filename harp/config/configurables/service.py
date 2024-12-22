from keyword import iskeyword
from typing import Literal, Optional

from pydantic import ConfigDict, Field, model_serializer, model_validator

from harp.services.models import ServiceDefinition

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
                if str.isidentifier(k) and not iskeyword(k):
                    arguments[k] = values.pop(k)
                else:
                    raise ValueError(f"Invalid field name: {k} for {cls.__name__}")
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

    def to_service_definition(
        self, name: str, lifestyle: Optional[Literal["singleton", "transient", "scoped"]] = "singleton"
    ) -> ServiceDefinition:
        """Convert the service settings to a service definition."""
        return ServiceDefinition(
            name=name,
            base=self.base,
            type=self.type,
            constructor=self.constructor,
            arguments=self.arguments,
            lifestyle=lifestyle,
        )


class LazyService(BaseConfigurable):
    """A lazy service definition, that will be resolved at runtime."""

    type: str | list[str] = Field(..., description="Reference to the service to resolve at runtime.")

    def resolve(self, resolver, context):
        """
        Resolve reference value in using the given resolver (callable) and resolution context.
        """
        return resolver(self.type, context)

    @model_serializer(mode="wrap")
    def __serialize(self, wrapped, context):
        """Enhance serialization logic to inline arguments, unless they conflict with a model field."""
        return wrapped(self, context)

from typing import Annotated, Generic, Optional, Self, Type, TypeVar

from pydantic import BaseModel, Field, field_serializer, model_serializer, model_validator


class FactoryDefinition(BaseModel):
    pass


class BaseConfigurable(BaseModel):
    @classmethod
    def from_dict(cls: Type[Self], data: dict) -> Self:
        return cls(**data)

    @classmethod
    def from_kwargs(cls: Type[Self], **kwargs) -> Self:
        return cls(**kwargs)

    def __getitem__(self, item):
        value = self
        for bit in item.split("."):
            value = getattr(value, bit)
        return value


class Configurable(BaseConfigurable):
    class Config:
        extra = "forbid"


TConfigurable = TypeVar("TConfigurable", bound=Configurable)


class Stateful(BaseConfigurable, Generic[TConfigurable]):
    settings: Annotated[TConfigurable, Field(repr=False)]

    @classmethod
    def get_settings_type(cls) -> Type[Configurable]:
        return cls.model_fields["settings"].annotation

    @classmethod
    def from_settings_dict(cls: Type[Self], data: dict) -> Self:
        settings_type = cls.get_settings_type()
        return cls(settings=settings_type(**data))

    @classmethod
    def from_settings_kwargs(cls: Type[Self], **kwargs) -> Self:
        settings_type = cls.get_settings_type()
        return cls(settings=settings_type(**kwargs))

    @field_serializer("settings", when_used="json")
    @classmethod
    def __serialize_settings(cls, settings: TConfigurable):
        BaseType = type(settings).__mro__[type(settings).__mro__.index(Configurable) - 1]
        return BaseType.model_construct(
            **{k: v for k, v in settings.model_dump().items() if k in BaseType.model_fields}
        ).model_dump()


class Service(Configurable):
    class Config:
        extra = "allow"

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

        return {**data, **({"arguments": arguments} if len(arguments) else {}), **inline_arguments}

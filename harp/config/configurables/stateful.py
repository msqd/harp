from typing import Annotated, Generic, Self, Type, TypeVar

from pydantic import Field, field_serializer

from .base import BaseConfigurable, Configurable

TSettings = TypeVar("TSettings", bound=Configurable)


class Stateful(BaseConfigurable, Generic[TSettings]):
    """
    A base class for stateful objects that are related to a settings class. Usually, it's used for live status of
    settings-defined objects, that may vary over time. It allows to separate the concerns of the imuatable,
    environment-provided settings, and the mutable, runtime-related state of the object.

    """

    settings: Annotated[TSettings, Field(repr=False)]

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
    def __serialize_settings(cls, settings: TSettings):
        BaseType = type(settings).__mro__[type(settings).__mro__.index(Configurable) - 1]
        return BaseType.model_construct(
            **{k: v for k, v in settings.model_dump().items() if k in BaseType.model_fields}
        ).model_dump()

from typing import Annotated, Generic, Self, Type, TypeVar

from pydantic import BaseModel, Field, field_serializer


class BaseConfigurable(BaseModel):
    @classmethod
    def from_dict(cls: Type[Self], data: dict) -> Self:
        return cls(**data)

    @classmethod
    def from_kwargs(cls: Type[Self], **kwargs) -> Self:
        return cls(**kwargs)


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

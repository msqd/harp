from typing import Generic, Self, Type, TypeVar, get_args

from pydantic import BaseModel


class Configurable(BaseModel):
    class Config:
        extra = "forbid"

    @classmethod
    def from_dict(cls: Type[Self], data: dict) -> Self:
        return cls(**data)

    @classmethod
    def from_kwargs(cls: Type[Self], **kwargs) -> Self:
        return cls(**kwargs)


TWrappedConfigurable = TypeVar("TWrappedConfigurable", bound=Configurable)


class StatefulConfigurableWrapper(Generic[TWrappedConfigurable]):
    settings: TWrappedConfigurable

    def __init__(self, settings: TWrappedConfigurable):
        self.settings = settings

    def __getattr__(self, item: str):
        try:
            return getattr(self.settings, item)
        except AttributeError as exc:
            raise AttributeError(
                f"'{type(self).__name__}' and wrapped '{type(self.settings).__name__}' objects have no attribute '{item}'"
            ) from exc

    @classmethod
    def from_settings_dict(cls: Type[Self], data: dict) -> Self:
        # this is probably weak in case of multiple inheritance, it assumes too much
        wrapped_type = get_args(cls.__orig_bases__[0])[0]
        return cls(wrapped_type(**data))

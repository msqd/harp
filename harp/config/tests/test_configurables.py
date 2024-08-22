from typing import Generic, Optional, Tuple, TypeVar

from httpx import AsyncClient
from pydantic import BaseModel

from harp.config.configurables import Configurable

TBase = TypeVar("TBase")


def import_entity(name: str):
    _path, _attr = name.rsplit(".", 1)
    return getattr(__import__(_path), _attr)


class FactoryDefinition(BaseModel, Generic[TBase]):
    class Config:
        extra = "allow"

    type: str
    args: Optional[Tuple] = None

    def build(self, *args, **kwargs):
        Type = import_entity(self.type)
        return Type(*(self.args or ()), *args, **(self.model_extra or {}), **kwargs)


class SomeStuff(Configurable):
    service: FactoryDefinition[AsyncClient] = FactoryDefinition(type="httpx.AsyncClient", verify=False)


def test_configurable_factory():
    stuff = SomeStuff()

    service = stuff.service.build()
    assert isinstance(service, AsyncClient)

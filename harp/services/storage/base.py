from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass


class Storage(ABC):
    @contextmanager
    def store(self, entity, *, mode="save"):
        try:
            yield entity
        finally:
            if mode == "save":
                self.save(entity)

    @abstractmethod
    def select(self, _type):
        raise NotImplementedError()

    @abstractmethod
    def save(self, entity):
        raise NotImplementedError()


@dataclass(frozen=True)
class BaseStorageSettings:
    type: str

    @classmethod
    def build(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if k in cls.__dataclass_fields__})

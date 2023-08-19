from abc import ABC, abstractmethod
from contextlib import contextmanager


class Storage(ABC):
    @contextmanager
    def store(self, entity):
        try:
            yield entity
        finally:
            self.save(entity)

    @abstractmethod
    def select(self, _type):
        raise NotImplementedError()

    @abstractmethod
    def save(self, entity):
        raise NotImplementedError()

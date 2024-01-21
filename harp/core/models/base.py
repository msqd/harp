from typing import Any, Generic, TypeVar

from dataclasses_jsonschema import JsonSchemaMixin


class Entity(JsonSchemaMixin):
    id: Any


TResult = TypeVar("TResult")


class Results(Generic[TResult]):
    def __init__(self):
        self.items: list[TResult] = []
        self.meta = {}

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def append(self, item: TResult):
        self.items.append(item)

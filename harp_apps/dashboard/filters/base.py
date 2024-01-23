from functools import cached_property

from harp.typing.storage import Storage


class AbstractFacet:
    name = None
    choices = set()

    def __init__(self):
        self.meta = {}

    @cached_property
    def values(self):
        return [{"name": choice, "count": self.meta.get(choice, {}).get("count", None)} for choice in self.choices]

    def get_filter(self, raw_data: list):
        query_endpoints = self.choices.intersection(raw_data)
        return list(query_endpoints) if len(query_endpoints) else None

    def filter(self, raw_data: list):
        return {
            "values": self.values,
            "current": self.get_filter(raw_data),
        }


class FacetWithStorage(AbstractFacet):
    def __init__(self, *, storage: Storage):
        super().__init__()
        self.storage = storage

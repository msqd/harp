from typing import Optional, Union

from multidict import MultiDictProxy

from harp_apps.dashboard.filters.utils import flatten_facet_value, str_to_float_or_none
from harp_apps.storage.types import IStorage


class AbstractFacet:
    name = "name"

    def __init__(self):
        self.meta = {}

    @property
    def values(self):
        raise NotImplementedError

    def get_filter(self, raw_data: list):
        raise NotImplementedError

    def filter(self, raw_data: list):
        raise NotImplementedError

    def get_filter_from_query(self, query: MultiDictProxy):
        raise NotImplementedError

    def filter_from_query(self, query: MultiDictProxy):
        raise NotImplementedError


class AbstractChoicesFacet(AbstractFacet):
    choices: Union[set | list] = set()
    exhaustive = True

    @property
    def values(self):
        return [{"name": choice, "count": self.meta.get(choice, {}).get("count", None)} for choice in self.choices]

    def get_filter(self, raw_data: list):
        query_endpoints = set(self.choices).intersection(raw_data)
        return list(query_endpoints) if len(query_endpoints) else None

    def get_filter_from_query(self, query: MultiDictProxy):
        raw_data = self._choices_from_query(query)
        return self.get_filter(raw_data)

    def filter(self, raw_data: list):
        return {
            "values": self.values,
            "current": self.get_filter(raw_data),
        }

    def filter_from_query(self, query: MultiDictProxy):
        raw_data = self._choices_from_query(query)
        return self.filter(raw_data)

    def _choices_from_query(self, query: MultiDictProxy):
        return flatten_facet_value(query.getall(self.name, []))


class FacetWithStorage(AbstractChoicesFacet):
    def __init__(self, *, storage: IStorage):
        super().__init__()
        self.storage = storage


class AbstractMinMaxFacet(AbstractFacet):
    min: float = 0.0
    max: float = 100.0

    @property
    def values(self):
        return {
            "min": self.meta.get("min", None),
            "max": self.meta.get("max", None),
        }

    def filter(self, min, max):
        return {
            "values": ["min", "max"],
            "current": self.get_filter(min, max),
        }

    def filter_from_query(self, query: MultiDictProxy):
        min, max = self._min_max_from_query(query)
        return self.filter(min, max)

    def get_filter(self, min: Optional[float], max: Optional[float]):
        return {"min": min, "max": max}

    def get_filter_from_query(self, query: MultiDictProxy):
        min, max = self._min_max_from_query(query)
        return self.get_filter(min, max)

    def _min_max_from_query(self, query: MultiDictProxy):
        return str_to_float_or_none(query.get(self.name + "min", "")), str_to_float_or_none(
            query.get(self.name + "max", "")
        )


class NonExhaustiveFacet(AbstractChoicesFacet):
    exhaustive = False
    fallback_name = "NULL"

    def __init__(self):
        super().__init__()
        self.choices = list(self.choices) + [
            "NULL",
        ]

    def filter(self, raw_data: list):
        return {
            "values": self.values,
            "current": self.get_filter(raw_data),
            "fallbackName": self.fallback_name,
        }

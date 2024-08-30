from collections import ChainMap
from itertools import chain, combinations

from multidict import CIMultiDict

from harp.typing import NotSet


class MultiChainMap(ChainMap):
    """
    Implements the logic of chainmap, but for multidicts. It also allows to unset values on some key, this will be used
    for headers, cookies, query string ... to allow the user to rewrite requests/responses in a memory efficient way.

    The current implementation is neither complete, nor optimized.

    TODO: find a better way for __iter__
    """

    def __getitem__(self, key):
        x = super().__getitem__(key)
        if x is NotSet:
            return self.__missing__(key)
        return x

    def __delitem__(self, key):
        if key not in self:
            return super().__delitem__(key)
        self.maps[0][key] = NotSet

    def __contains__(self, key):
        if key in self.maps[0] and self.maps[0][key] is NotSet:
            return False
        return super().__contains__(key)

    def __len__(self):
        return len(list(self.__iter__()))

    def items(self):
        # TODO this needs a better algorithm (that does not involve creating a lot of multidicts)
        d = CIMultiDict()
        for mapping in reversed(self.maps):
            d.update(CIMultiDict(((k, v) for k, v in mapping.items())))
        return [(k, v) for k, v in d.items() if v is not NotSet]

    def __iter__(self):
        # TODO this needs a better algorithm (that does not involve creating a lot of multidicts)
        d = CIMultiDict()
        for mapping in reversed(self.maps):
            d.update(CIMultiDict(((k, v) for k, v in mapping.items())))
        return iter(CIMultiDict(((k, v) for k, v in d.items() if v is not NotSet)))

    def pop(self, key):
        # it has already been unset, or is not there
        if not self.__contains__(key):
            raise KeyError(f"Key not found in the first mapping: {key!r}")

        # otherwise, it's simpler to just set it as not set
        value = self[key]
        self[key] = NotSet
        return value

    def popitem(self):
        raise NotImplementedError()


def all_combinations(iterable):
    return set(chain(*(combinations(iterable, n + 1) for n in range(len(iterable)))))

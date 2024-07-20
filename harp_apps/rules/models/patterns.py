import re
from weakref import WeakValueDictionary


class Pattern:
    _instances = WeakValueDictionary()

    def __new__(cls, source: str, /):
        source = source.strip()
        if source not in cls._instances:
            # we need to store the instance in a separate var, or it will be garbage collected instantly
            instance = super().__new__(cls)
            # store the instance in the weakref dict
            cls._instances[source] = instance
        return cls._instances[source]

    def __init__(self, source: str, /):
        self._source = source
        self._pattern = re.compile("^" + ".*".join([re.escape(x) for x in source.split("*")]) + "$")

    @property
    def source(self):
        return self._source

    def __repr__(self):
        return "Pattern(%r)" % self._source

    def match(self, value: str, /):
        return self._pattern.match(value)

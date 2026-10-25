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
        self._parts = source.split("*")

    @property
    def source(self):
        return self._source

    def __repr__(self):
        return "Pattern(%r)" % self._source

    def match(self, value: str, /, *, trailing_slash: bool = False):
        """
        Match a value. With ``trailing_slash``, a ``<METHOD> <path>`` pattern whose path has no wildcard also matches
        the value with its final slash removed.
        """
        if self._glob(value):
            return True
        if trailing_slash and value.endswith("/"):
            _, space, path = self._source.partition(" ")
            if space and "*" not in path:
                return self._glob(value[:-1])
        return False

    def _glob(self, value: str, /) -> bool:
        """Glob-style match, "*" standing for any run of characters, in time linear in the length of value."""
        first, *rest = self._parts
        if not rest:
            return value == first
        *middle, last = rest

        if not value.startswith(first) or not value.endswith(last):
            return False
        position, end = len(first), len(value) - len(last)
        if position > end:
            return False

        # Leftmost placement of each inner segment leaves the most room for the next ones, so no backtracking.
        for part in middle:
            found = value.find(part, position, end)
            if found < 0:
                return False
            position = found + len(part)
        return True

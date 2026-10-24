import dataclasses

#: What replaces the value of a credential in anything HARP stores.
REDACTED = "REDACTED"

#: Header names redacted when no rule says otherwise (lower case).
DEFAULT_REDACTED_HEADERS = ("authorization", "proxy-authorization", "cookie", "set-cookie")


class HeaderNames(set):
    """A set of HTTP header names: field names are case-insensitive, so they are kept lower case."""

    def __init__(self, names=()):
        super().__init__(str(name).lower() for name in names)

    def __contains__(self, name):
        return super().__contains__(str(name).lower())

    def add(self, name):
        super().add(str(name).lower())

    def discard(self, name):
        super().discard(str(name).lower())

    def remove(self, name):
        super().remove(str(name).lower())

    def update(self, *others):
        for names in others:
            for name in names:
                self.add(name)


@dataclasses.dataclass(kw_only=True)
class Redaction:
    """Which values are credentials, and so replaced by :data:`REDACTED` before anything is stored.

    A rule edits the sets of its transaction (``transaction.redaction.headers.add("x-api-key")``).
    ``headers`` applies to request and response headers alike; ``query`` names are matched exactly.
    """

    headers: HeaderNames = dataclasses.field(default_factory=lambda: HeaderNames(DEFAULT_REDACTED_HEADERS))
    query: set = dataclasses.field(default_factory=set)

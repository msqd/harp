from functools import lru_cache
from inspect import signature


@lru_cache(maxsize=1024)
def _cached_signature(subject):
    """Memoize signature introspection: controllers are long-lived, so their prototype never
    changes, and this runs on every request.

    Two constraints come from caching on the subject itself, which a plain ``signature()`` call did
    not impose. Both are satisfied by today's controllers, which are long-lived and hashed by
    identity, so this is a note for whoever writes the next one:

    - The controller must be **hashable**. An unhashable one raises ``TypeError`` here rather than
      resolving, because it cannot be used as a cache key.
    - The cache holds a **strong reference** to every controller it has seen. Controllers created
      per request or per connection would therefore be pinned, up to ``maxsize``, and would never
      hit the cache anyway.
    """
    return signature(subject)


def resolve_arguments(subject, **candidates) -> list:
    """
    Dynamically resolve positional arguments by names in the prototype of ``subject``, looking at a "candidates"
    dictionary that contains the possible arguments. Parameters missing from candidates fall back to their default.
    """
    try:
        return [
            (candidates[name] if name in candidates or param.default is param.empty else param.default)
            for name, param in _cached_signature(subject).parameters.items()
            if param.kind is not param.KEYWORD_ONLY
        ]
    except KeyError as exc:
        raise TypeError(f"Unable to resolve arguments: {exc}")

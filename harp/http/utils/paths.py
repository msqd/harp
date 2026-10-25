import re
from urllib.parse import urlsplit

_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")
_ENCODED_SLASH = re.compile(r"%2F", re.IGNORECASE)


def _decode_unreserved(match: re.Match) -> str:
    char = chr(int(match.group(1), 16))
    return char if char in _UNRESERVED else match.group(0)


def _collapse(path: str) -> str:
    """Drop the empty segments, the ``;`` parameters of each segment and the trailing slash, as common upstreams do."""
    segments = (segment.partition(";")[0] for segment in path.split("/"))
    return "/" + "/".join(segment for segment in segments if segment)


def _unreserved_decoded(target: str) -> str | None:
    """The path with unreserved escapes decoded, ``None`` for an authority urlsplit cannot parse."""
    try:
        path = urlsplit(target).path
    except ValueError:
        return None
    return _ESCAPE.sub(_decode_unreserved, path or "/")


def normalize_path(target: str) -> str:
    """
    The path of a request target as rules match it, not as it is forwarded (the proxy forwards it unchanged): a
    leading scheme and authority are removed, the query is dropped, percent-escapes of unreserved characters are
    decoded (RFC 3986 §2.3), and empty segments, ``;`` parameters and the trailing slash are dropped. Other escapes,
    ``%2F`` included, stay as sent (see :func:`normalize_path_variants`).
    """
    path = _unreserved_decoded(target)
    if path is None:  # the request is refused later, match what was received
        return _ESCAPE.sub(_decode_unreserved, target)
    return _collapse(path)


def normalize_path_variants(target: str) -> list[str]:
    """
    Other readings of the path that an upstream may act on: with ``%2F`` taken as a slash. Empty when the path has
    no such escape.
    """
    path = _unreserved_decoded(target)
    if path is None or not _ENCODED_SLASH.search(path):
        return []
    return [_collapse(_ENCODED_SLASH.sub("/", path))]

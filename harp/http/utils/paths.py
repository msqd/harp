import re
from urllib.parse import urlsplit

_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")


def _decode_unreserved(match: re.Match) -> str:
    char = chr(int(match.group(1), 16))
    return char if char in _UNRESERVED else match.group(0)


def normalize_path(target: str) -> str:
    """
    The path of a request target as the proxy forwards it: a leading scheme and authority are removed, the query is
    dropped, and percent-escapes of unreserved characters are decoded (RFC 3986 §2.3). Other escapes stay as sent.
    """
    try:
        path = urlsplit(target).path
    except ValueError:  # an authority urlsplit cannot parse: the request is refused later, match what was received
        path = target
    return _ESCAPE.sub(_decode_unreserved, path or "/")

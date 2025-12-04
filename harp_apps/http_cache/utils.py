from hishel import Headers
from multidict import CIMultiDict

from harp.utils.bytes import ensure_str


def prepare_headers_for_serialization(headers, /, *, varying=()) -> tuple[bytes, dict[str, str], dict[str, str]]:
    """Prepare headers for serialization.

    Args:
        headers: Either a list of (bytes, bytes) tuples (hishel 0.1.x / httpcore)
                 or a Headers mapping (hishel 1.0)
        varying: Tuple of header names that should be stored separately

    Returns:
        Tuple of (static_headers_bytes, varying_headers_dict, metadata_dict)
    """
    static_headers = []
    varying_headers = {}
    metadata = {}

    # Handle both old list format and new Headers mapping
    if hasattr(headers, "items"):
        # hishel 1.0: Headers is a MutableMapping
        header_items = [
            (
                k.encode() if isinstance(k, str) else k,
                str(v).encode() if not isinstance(v, bytes) else v,
            )
            for k, v in headers.items()
        ]
    else:
        # hishel 0.1.x / httpcore: list of (bytes, bytes) tuples
        header_items = headers

    for k, v in header_items:
        k = k.lower().strip()
        if k in varying:
            varying_headers[k.decode()] = v.decode()
        else:
            static_headers.append(b": ".join((k, v)))

        if k == b"content-type":
            metadata["content-type"] = v.decode()

    return b"\n".join(static_headers), varying_headers, metadata


def _parse_header(header: bytes) -> tuple[str, str]:
    splitted = header.split(b": ", 1)
    return (ensure_str(splitted[0]), ensure_str(splitted[1]))


def deserialize_headers(headers: bytes, /, *, varying: dict) -> Headers:
    """
    Deserialize headers for hishel.

    :param headers: blob content to be deserialized
    :param varying: additional headers to be included
    :return: hishel Headers
    """
    return Headers(
        CIMultiDict(
            (
                *(_parse_header(header) for header in headers.split(b"\n") if header),
                *((ensure_str(k), ensure_str(v)) for k, v in varying.items()),
            )
        )
    )

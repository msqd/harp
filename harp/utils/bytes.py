def ensure_bytes(x):
    if isinstance(x, bytes):
        return x
    return bytes(x, "utf-8")


def ensure_str(x):
    if isinstance(x, str):
        return x
    return str(x, "utf-8")


HEADER_ENCODING = "latin-1"
"""Header values are opaque octets (RFC 9110 §5.5, obs-text): one char per byte, whatever the bytes are."""


def header_bytes(x):
    """Encode a header name or value for the wire. Latin-1 round-trips what we decoded, utf-8 covers the rest."""
    if isinstance(x, bytes):
        return x
    try:
        return x.encode(HEADER_ENCODING)
    except UnicodeEncodeError:
        return x.encode("utf-8")


def header_str(x):
    """Decode a header name or value from the wire. Never fails, and :func:`header_bytes` gives the bytes back."""
    if isinstance(x, str):
        return x
    return x.decode(HEADER_ENCODING)


def header_display(x: str) -> str:
    """Readable text for a wire-form (latin-1) header: utf-8 when the bytes are valid utf-8, else as is."""
    try:
        return x.encode(HEADER_ENCODING).decode("utf-8")
    except UnicodeError:
        return x

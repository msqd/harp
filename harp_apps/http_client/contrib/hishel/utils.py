from harp.utils.bytes import ensure_bytes


def prepare_headers_for_serialization(
    headers: list[tuple[bytes, bytes]], /, *, varying=()
) -> tuple[bytes, dict[str, str], dict[str, str]]:
    static_headers = []
    varying_headers = {}
    metadata = {}

    for k, v in headers:
        k = k.lower().strip()
        if k in varying:
            varying_headers[k.decode()] = v.decode()
        else:
            static_headers.append(b": ".join((k, v)))

        if k == b"content-type":
            metadata["content-type"] = v.decode()

    return b"\n".join(static_headers), varying_headers, metadata


def _parse_header(header: bytes) -> tuple[bytes, bytes]:
    splitted = header.split(b": ", 1)
    return (splitted[0], splitted[1])


def prepare_headers_for_deserialization(headers: bytes, /, *, varying: dict) -> list[tuple[bytes, bytes]]:
    return [
        *(_parse_header(header) for header in headers.split(b"\n")),
        *((ensure_bytes(k), ensure_bytes(v)) for k, v in varying.items()),
    ]

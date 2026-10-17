from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    """An HTTP client HARP can send requests with: the httpx transport that does the actual work."""

    transport_type: str


_CLIENTS = {
    "httpx": Client("httpx.AsyncHTTPTransport"),
    "aiohttp": Client("harp_apps.http_client.aiohttp_transport.AiohttpTransport"),
}

CLIENTS = tuple(_CLIENTS)
DEFAULT_CLIENT = "httpx"


def get_client(name: str) -> Client:
    try:
        return _CLIENTS[name]
    except KeyError:
        raise ValueError(f"Unknown client {name!r}, choose one of: {', '.join(CLIENTS)}.") from None

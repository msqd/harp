"""The httpx transports HARP is tested against, by full class path (as `http_client.transport.type` takes them)."""

import importlib

TRANSPORT_TYPES = (
    "httpx.AsyncHTTPTransport",
    "harp_apps.http_client.aiohttp_transport.AiohttpTransport",
)


def transport_class(path: str) -> type:
    module, _, name = path.rpartition(".")
    return getattr(importlib.import_module(module), name)

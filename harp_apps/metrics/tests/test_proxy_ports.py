from unittest.mock import Mock

from harp.config import OnReadyEvent
from harp.controllers import ProxyControllerResolver
from harp_apps.metrics.__app__ import on_ready

METRICS_PATH = "/.prometheus/metrics"


async def upstream_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": b"from the proxied upstream"})


async def get(app, path: str) -> tuple[int, bytes]:
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    return status, b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")


async def test_metrics_path_is_proxied_like_any_other_path_on_proxy_ports():
    provider = Mock()
    provider.get.side_effect = lambda key: ProxyControllerResolver() if key is ProxyControllerResolver else Mock()
    event = OnReadyEvent(provider, upstream_app, [])

    await on_ready(event)

    assert await get(event.asgi_app, METRICS_PATH) == (200, b"from the proxied upstream")

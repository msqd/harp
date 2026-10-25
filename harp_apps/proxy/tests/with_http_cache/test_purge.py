"""PURGE through the whole proxy: the allow-list reads the peer address HARP sees, whatever the headers claim (#801)."""

import pytest
import respx
from httpx import Response

from harp.config import ConfigurationBuilder
from harp.utils.testing.communicators import ASGICommunicator

ALLOWED_PEER = ("10.0.0.5", 51000)
OTHER_PEER = ("192.168.0.9", 51000)


async def _app(*, purge=None, trusted_proxies=()):
    builder = ConfigurationBuilder(
        {
            "applications": ["http_client", "http_cache", "proxy"],
            "http_cache": {"purge": purge or {}},
            "proxy": {
                "trusted_proxies": list(trusted_proxies),
                "endpoints": [{"name": "api", "port": 80, "url": "http://api.example.com/"}],
            },
        },
        use_default_applications=False,
    )
    system = await builder.abuild_system(validate_dependencies=False)
    communicator = ASGICommunicator(system.asgi_app)
    await communicator.asgi_lifespan_startup()
    return communicator


@pytest.mark.asyncio
async def test_allowed_peer_purges_one_entry_without_reaching_the_upstream():
    app = await _app(purge={"enabled": True, "allow": ["10.0.0.0/24"]})
    with respx.mock:
        get = respx.get("http://api.example.com/data").mock(
            return_value=Response(200, headers={"Cache-Control": "max-age=3600"})
        )
        purge = respx.route(method="PURGE").mock(return_value=Response(500))

        await app.http_request("GET", "/data", client=ALLOWED_PEER)
        assert (await app.http_request("PURGE", "/data", client=ALLOWED_PEER))["status"] == 200
        assert (await app.http_request("PURGE", "/data", client=ALLOWED_PEER))["status"] == 404
        await app.http_request("GET", "/data", client=ALLOWED_PEER)

        assert get.call_count == 2
        assert purge.call_count == 0


@pytest.mark.asyncio
async def test_forwarded_header_does_not_make_a_peer_allowed():
    """Even when the peer is a trusted proxy: the allow-list is about who connects to HARP."""
    app = await _app(
        purge={"enabled": True, "allow": ["10.0.0.0/24"]},
        trusted_proxies=["192.168.0.0/24"],
    )
    with respx.mock:
        get = respx.get("http://api.example.com/data").mock(
            return_value=Response(200, headers={"Cache-Control": "max-age=3600"})
        )
        headers = [(b"x-forwarded-for", b"10.0.0.5"), (b"forwarded", b"for=10.0.0.5")]

        await app.http_request("GET", "/data", client=OTHER_PEER)
        response = await app.http_request("PURGE", "/data", headers=headers, client=OTHER_PEER)
        await app.http_request("GET", "/data", client=OTHER_PEER)

        assert response["status"] == 403
        assert get.call_count == 1


@pytest.mark.asyncio
async def test_unknown_peer_is_refused():
    app = await _app(purge={"enabled": True, "allow": ["0.0.0.0/0", "::/0"]})
    with respx.mock:
        assert (await app.http_request("PURGE", "/data"))["status"] == 403


@pytest.mark.asyncio
async def test_purge_is_proxied_when_disabled():
    app = await _app()
    with respx.mock:
        purge = respx.route(method="PURGE").mock(return_value=Response(204))
        assert (await app.http_request("PURGE", "/data", client=ALLOWED_PEER))["status"] == 204
        assert purge.call_count == 1

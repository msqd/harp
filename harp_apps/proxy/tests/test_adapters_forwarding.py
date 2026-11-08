"""``X-Forwarded-For``, ``Forwarded`` and ``X-Real-IP`` are claims about who the client is. A client outside
``proxy.trusted_proxies`` may claim anything, so its values are stripped; a trusted proxy's are kept. Either way the
peer HARP actually talks to is appended, on the outgoing request only."""

from ipaddress import ip_network

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp_apps.proxy.adapters import HttpClientProxyAdapter

CLAIMS = {"X-Forwarded-For": "6.6.6.6", "Forwarded": "for=6.6.6.6", "X-Real-IP": "6.6.6.6"}


async def _outgoing(headers, peer, trusted=("10.0.0.0/8",)):
    async with AsyncClient() as client:
        adapter = HttpClientProxyAdapter(client, trusted_proxies=[ip_network(n) for n in trusted])
        request = HttpRequest(method="GET", path="/x", headers=headers, body=b"", client_ipaddr=peer)
        await request.aread()
        remote = adapter._build_request(request, "http://example.com/x")
    return request, remote.headers


@pytest.mark.asyncio
async def test_untrusted_peer_claims_are_replaced_by_the_peer():
    _, headers = await _outgoing(CLAIMS, "203.0.113.7")

    assert headers.get_list("x-forwarded-for") == ["203.0.113.7"]
    assert headers.get_list("forwarded") == ["for=203.0.113.7"]
    assert "x-real-ip" not in headers


@pytest.mark.asyncio
async def test_trusted_peer_claims_are_kept_and_the_peer_appended():
    _, headers = await _outgoing(CLAIMS, "10.1.2.3")

    assert headers.get_list("x-forwarded-for") == ["6.6.6.6, 10.1.2.3"]
    assert headers.get_list("forwarded") == ["for=6.6.6.6, for=10.1.2.3"]
    assert headers.get_list("x-real-ip") == ["6.6.6.6"]


@pytest.mark.asyncio
async def test_repeated_headers_from_a_trusted_peer_are_folded():
    async with AsyncClient() as client:
        adapter = HttpClientProxyAdapter(client, trusted_proxies=[ip_network("10.0.0.0/8")])
        request = HttpRequest(method="GET", path="/", headers={}, body=b"", client_ipaddr="10.0.0.1")
        await request.aread()
        request.headers.add("X-Forwarded-For", "1.1.1.1")
        request.headers.add("x-forwarded-for", "2.2.2.2")
        remote = adapter._build_request(request, "http://example.com/")

    assert remote.headers.get_list("x-forwarded-for") == ["1.1.1.1, 2.2.2.2, 10.0.0.1"]


@pytest.mark.asyncio
async def test_ipv6_peer_is_quoted_and_bracketed_in_forwarded():
    _, headers = await _outgoing({}, "2001:db8::1")

    assert headers.get_list("x-forwarded-for") == ["2001:db8::1"]
    assert headers.get_list("forwarded") == ['for="[2001:db8::1]"']


@pytest.mark.asyncio
async def test_ipv6_trusted_peer_is_matched_against_ranges():
    _, headers = await _outgoing({"X-Forwarded-For": "6.6.6.6"}, "fd00::5", trusted=("fd00::/8",))

    assert headers.get_list("x-forwarded-for") == ["6.6.6.6, fd00::5"]


@pytest.mark.asyncio
async def test_no_trusted_proxies_by_default():
    async with AsyncClient() as client:
        adapter = HttpClientProxyAdapter(client)
        request = HttpRequest(
            method="GET", path="/", headers={"X-Forwarded-For": "6.6.6.6"}, body=b"", client_ipaddr="127.0.0.1"
        )
        await request.aread()
        remote = adapter._build_request(request, "http://example.com/")

    assert remote.headers.get_list("x-forwarded-for") == ["127.0.0.1"]


@pytest.mark.asyncio
async def test_unknown_peer_is_untrusted_and_not_appended():
    _, headers = await _outgoing(CLAIMS, None)

    assert "x-forwarded-for" not in headers
    assert "forwarded" not in headers
    assert "x-real-ip" not in headers


@pytest.mark.asyncio
async def test_recorded_request_is_unchanged():
    request, _ = await _outgoing(CLAIMS, "203.0.113.7")

    assert request.headers["x-forwarded-for"] == "6.6.6.6"
    assert request.headers["forwarded"] == "for=6.6.6.6"
    assert request.headers["x-real-ip"] == "6.6.6.6"


@pytest.mark.asyncio
async def test_native_ipv6_peer_is_unchanged():
    _, headers = await _outgoing(CLAIMS, "fd00::1", trusted=("fd00::/8",))

    assert headers.get_list("forwarded") == ['for=6.6.6.6, for="[fd00::1]"']

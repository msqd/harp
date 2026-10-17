"""Credentials written in an endpoint url (``http://user:pass@host/``).

They are not part of the authority a ``Host`` header carries (RFC 9110 §7.2), so they are sent as
``Authorization: Basic`` instead, unless the request already carries an ``Authorization`` (client or
rule), and they never reach what is recorded about the request.
"""

import base64

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp_apps.proxy.adapters import HttpClientProxyAdapter

from .test_adapters_hop_by_hop import _forward, _header_lines


def _basic(value: str) -> str:
    return "basic " + base64.b64encode(value.encode()).decode()


@pytest.mark.asyncio
async def test_credentials_are_sent_as_basic_authorization_not_in_host():
    wire = await _forward({}, url_userinfo="user:p%40ss")

    lines = _header_lines(wire)
    assert f"authorization: {_basic('user:p@ss')}".lower() in lines
    assert not any(line.startswith("host:") and "@" in line for line in lines)
    assert any(line.startswith("host: 127.0.0.1:") for line in lines)


@pytest.mark.asyncio
async def test_request_authorization_wins():
    wire = await _forward({"Authorization": "Bearer abc"}, url_userinfo="user:pass")

    lines = _header_lines(wire)
    assert [line for line in lines if line.startswith("authorization:")] == ["authorization: bearer abc"]
    assert not any(line.startswith("host:") and "@" in line for line in lines)


@pytest.mark.asyncio
async def test_credentials_are_absent_from_recorded_remote_url():
    async with AsyncClient() as client:
        adapter = HttpClientProxyAdapter(client)
        request = HttpRequest(method="GET", path="/x", headers={}, body=b"")
        await request.aread()
        adapter._build_request(request, "http://user:secret@example.com:8080/x?a=1")

    assert request.extensions["remote_url"] == "http://example.com:8080/x?a=1"
    assert "authorization" not in request.headers
    assert request.headers["host"] == "example.com:8080"

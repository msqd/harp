"""The cache works below the transaction: what it needs to redact and to skip travels with the outgoing request."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from harp.http import HttpRequest
from harp.models import Transaction
from harp_apps.proxy.adapters import HttpClientProxyAdapter


def _build(transaction: Transaction | None):
    async def build():
        async with AsyncClient() as client:
            adapter = HttpClientProxyAdapter(client, extensions={"endpoint": "api"})
            request = HttpRequest(method="GET", path="/x", headers={}, body=b"")
            await request.aread()
            return adapter._build_request(request, "http://example.com/x", transaction=transaction)

    return build()


@pytest.mark.asyncio
async def test_extension_carries_the_redaction_and_markers_as_they_stand_once_rules_have_run():
    transaction = Transaction(type="http", started_at=datetime.now(UTC), markers={"skip-response-storage"})
    transaction.redaction.query.add("client_secret")

    extension = (await _build(transaction)).extensions["harp"]

    assert extension["endpoint"] == "api"
    assert extension["redaction"].query == {"client_secret"}
    assert "authorization" in extension["redaction"].headers
    assert extension["markers"] == {"skip-response-storage"}


@pytest.mark.asyncio
async def test_extension_without_a_transaction_has_neither():
    extension = (await _build(None)).extensions["harp"]

    assert "redaction" not in extension
    assert "markers" not in extension


@pytest.mark.asyncio
async def test_extension_carries_the_peer_address_not_a_forwarded_one():
    async with AsyncClient() as client:
        adapter = HttpClientProxyAdapter(client, extensions={"endpoint": "api"})
        request = HttpRequest(
            method="PURGE", path="/x", headers={"x-forwarded-for": "10.0.0.1"}, body=b"", client_ipaddr="192.168.0.9"
        )
        await request.aread()
        built = adapter._build_request(request, "http://example.com/x")

    assert built.extensions["harp"]["client_ip"] == "192.168.0.9"

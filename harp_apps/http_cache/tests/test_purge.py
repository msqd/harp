"""PURGE removes one cache entry, behind an opt-in allow-list of peer addresses (#801)."""

from ipaddress import ip_network

import httpx
import pytest
from hishel import SpecificationPolicy

from harp_apps.http_cache.settings import PurgeSettings
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.http_cache.records import MemoryCacheRecords

HOST = "http://origin.test"


class Origin(httpx.AsyncBaseTransport):
    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = {"cache-control": "max-age=3600", **(headers or {})}
        self.requests: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.raw_path.decode()))
        return httpx.Response(200, headers=self.headers, content=b"body")

    def count(self, method: str, target: str) -> int:
        return self.requests.count((method, target))


def make_transport(origin, purge) -> AsyncCacheTransport:
    return AsyncCacheTransport(
        next_transport=origin,
        storage=AsyncStorage(MemoryCacheRecords()),
        policy=SpecificationPolicy(),
        purge=purge,
    )


def make_client(transport, *, endpoint="api", peer: str | None = "127.0.0.1") -> httpx.AsyncClient:
    """A client talking to the cache the way the proxy does: endpoint and peer address come from the proxy."""

    async def hook(request: httpx.Request) -> None:
        request.extensions["harp"] = {"endpoint": endpoint, "client_ip": peer}

    return httpx.AsyncClient(transport=transport, event_hooks={"request": [hook]})


ENABLED = PurgeSettings(enabled=True, allow=["127.0.0.1", "10.0.0.0/8"])


def test_purge_is_disabled_by_default():
    assert PurgeSettings().enabled is False
    assert PurgeSettings().allow == [ip_network("127.0.0.1")]


@pytest.mark.asyncio
async def test_enabling_purge_alone_allows_local_purges():
    async with make_client(make_transport(Origin(), PurgeSettings(enabled=True))) as local:
        assert (await local.request("PURGE", f"{HOST}/item")).status_code == 404
    async with make_client(make_transport(Origin(), PurgeSettings(enabled=True)), peer="::1") as other:
        assert (await other.request("PURGE", f"{HOST}/item")).status_code == 403


@pytest.mark.asyncio
class TestPurgeAllowedPeer:
    async def test_removes_the_entry_and_answers_200(self):
        origin = Origin()
        async with make_client(make_transport(origin, ENABLED)) as client:
            await client.get(f"{HOST}/item")
            response = await client.request("PURGE", f"{HOST}/item")
            assert response.status_code == 200
            await client.get(f"{HOST}/item")
        assert origin.count("GET", "/item") == 2

    async def test_never_calls_the_upstream(self):
        origin = Origin()
        async with make_client(make_transport(origin, ENABLED)) as client:
            await client.get(f"{HOST}/item")
            await client.request("PURGE", f"{HOST}/item")
            await client.request("PURGE", f"{HOST}/missing")
        assert [method for method, _ in origin.requests] == ["GET"]

    async def test_answers_404_when_there_is_no_entry(self):
        async with make_client(make_transport(Origin(), ENABLED)) as client:
            response = await client.request("PURGE", f"{HOST}/missing")
        assert response.status_code == 404

    async def test_second_purge_answers_404(self):
        async with make_client(make_transport(Origin(), ENABLED)) as client:
            await client.get(f"{HOST}/item")
            assert (await client.request("PURGE", f"{HOST}/item")).status_code == 200
            assert (await client.request("PURGE", f"{HOST}/item")).status_code == 404

    async def test_query_string_is_part_of_the_target(self):
        origin = Origin()
        async with make_client(make_transport(origin, ENABLED)) as client:
            await client.get(f"{HOST}/item?a=1")
            await client.get(f"{HOST}/item?a=2")
            await client.request("PURGE", f"{HOST}/item?a=1")
            await client.get(f"{HOST}/item?a=1")
            await client.get(f"{HOST}/item?a=2")
        assert origin.count("GET", "/item?a=1") == 2
        assert origin.count("GET", "/item?a=2") == 1

    async def test_other_paths_are_untouched(self):
        origin = Origin()
        async with make_client(make_transport(origin, ENABLED)) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
            await client.request("PURGE", f"{HOST}/item")
            await client.get(f"{HOST}/other")
        assert origin.count("GET", "/other") == 1

    async def test_other_endpoints_are_untouched(self):
        origin = Origin()
        transport = make_transport(origin, ENABLED)
        async with make_client(transport, endpoint="one") as one, make_client(transport, endpoint="two") as two:
            await one.get(f"{HOST}/item")
            await two.get(f"{HOST}/item")
            assert (await one.request("PURGE", f"{HOST}/item")).status_code == 200
            await two.get(f"{HOST}/item")
            await one.get(f"{HOST}/item")
        assert origin.count("GET", "/item") == 3

    async def test_removes_every_variant(self):
        origin = Origin({"vary": "accept"})
        async with make_client(make_transport(origin, ENABLED)) as client:
            for accept in ("text/html", "application/json"):
                await client.get(f"{HOST}/item", headers={"accept": accept})
            await client.request("PURGE", f"{HOST}/item")
            for accept in ("text/html", "application/json"):
                await client.get(f"{HOST}/item", headers={"accept": accept})
        assert origin.count("GET", "/item") == 4

    @pytest.mark.parametrize("peer", ["127.0.0.1", "10.1.2.3", "::ffff:127.0.0.1"])
    async def test_peers_in_the_allow_list(self, peer):
        async with make_client(make_transport(Origin(), ENABLED), peer=peer) as client:
            response = await client.request("PURGE", f"{HOST}/item")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestPurgeForbidden:
    @pytest.mark.parametrize("peer", ["192.168.0.1", "::1", "not-an-ip", "", None])
    async def test_peer_outside_the_allow_list_is_refused_and_the_entry_stays(self, peer):
        origin = Origin()
        transport = make_transport(origin, ENABLED)
        async with make_client(transport) as allowed, make_client(transport, peer=peer) as client:
            await allowed.get(f"{HOST}/item")
            response = await client.request("PURGE", f"{HOST}/item")
            await allowed.get(f"{HOST}/item")
        assert response.status_code == 403
        assert origin.requests == [("GET", "/item")]

    async def test_enabled_with_an_empty_allow_list_refuses_everyone(self):
        purge = PurgeSettings(enabled=True, allow=[])
        async with make_client(make_transport(Origin(), purge)) as client:
            assert (await client.request("PURGE", f"{HOST}/item")).status_code == 403


@pytest.mark.asyncio
class TestPurgeDisabled:
    @pytest.mark.parametrize("purge", [None, PurgeSettings(), PurgeSettings(allow=["127.0.0.1"])])
    async def test_request_is_proxied_as_before(self, purge):
        origin = Origin()
        async with make_client(make_transport(origin, purge)) as client:
            response = await client.request("PURGE", f"{HOST}/item")
        assert response.text == "body"
        assert origin.count("PURGE", "/item") == 1

"""What the cache keeps is redacted like the transaction record, or not kept at all (ADR-0009)."""

from dataclasses import replace

import hashlib

import httpx
from sqlalchemy import select
from hishel import CacheOptions, Headers, SpecificationPolicy

from harp.models.redaction import REDACTED, Redaction
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.constants import SKIP_REQUEST_STORAGE, SKIP_RESPONSE_STORAGE, SKIP_STORAGE
from harp_apps.http_cache.models import CacheBody, CacheResource, CacheStats, CacheVariant
from harp_apps.http_cache.records import MemoryCacheRecords
from harp_apps.http_cache.records.sql import SqlCacheRecords

URL = "http://origin.test/item"


class Origin(httpx.AsyncBaseTransport):
    def __init__(self, **headers: str):
        self.headers = {"cache-control": "public, max-age=3600", **headers}
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(200, headers=self.headers, content=b"body")


class Setup:
    def __init__(self, origin: Origin, harp: dict, records=None):
        self.origin = origin
        self.records = records or MemoryCacheRecords()
        self.storage = AsyncStorage(self.records)
        transport = AsyncCacheTransport(
            next_transport=origin,
            storage=self.storage,
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )

        async def extend(request: httpx.Request) -> None:
            request.extensions["harp"] = {"endpoint": "api", **harp}

        self.client = httpx.AsyncClient(transport=transport, event_hooks={"request": [extend]})

    async def stored_heads(self) -> list[str]:
        """What the cache keeps of the requests and responses it stored, headers included."""
        return [
            variant.record.head.decode()
            for key in await self.records.list_keys()
            for variant in await self.records.get_variants(key)
        ]

    async def fetch_twice(self, url: str = URL, **headers: str) -> int:
        async with self.client:
            await self.client.get(url, headers=headers)
            await self.client.get(url, headers=headers)
        return self.origin.calls


def redaction(*, headers_out=(), headers_in=(), query=()) -> Redaction:
    result = Redaction()
    result.headers.update(headers_in)
    for name in headers_out:
        result.headers.discard(name)
    result.query.update(query)
    return result


async def test_a_response_is_cached_and_its_stored_request_headers_hold_no_credential():
    setup = Setup(Origin(), {"redaction": redaction()})

    assert await setup.fetch_twice(authorization="Bearer secret-token", accept="*/*") == 1

    (headers,) = [text for text in await setup.stored_heads() if "accept" in text]
    assert f"authorization: {REDACTED}" in headers
    assert "secret-token" not in headers
    assert "accept: */*" in headers


async def test_a_request_outside_a_proxied_transaction_gets_the_default_set():
    setup = Setup(Origin(), {})

    await setup.fetch_twice(authorization="Bearer secret-token")

    assert not any("secret-token" in text for text in await setup.stored_heads())


async def test_a_response_varying_on_a_redacted_header_is_not_cached():
    setup = Setup(Origin(vary="Authorization"), {"redaction": redaction()})

    assert await setup.fetch_twice(authorization="Bearer secret-token") == 2
    assert await setup.records.list_keys() == []


async def test_vary_is_matched_whatever_the_case_and_among_other_names():
    setup = Setup(Origin(vary="Accept-Encoding, COOKIE"), {"redaction": redaction()})

    assert await setup.fetch_twice() == 2


async def test_a_response_carrying_a_redacted_response_header_is_not_cached():
    setup = Setup(Origin(**{"set-cookie": "sid=abc"}), {"redaction": redaction()})

    assert await setup.fetch_twice() == 2
    assert await setup.records.list_keys() == []


async def everything(records) -> str:
    """Every value any cache table holds."""
    if isinstance(records, SqlCacheRecords):
        async with records.engine.connect() as conn:
            return "".join(
                [
                    str((await conn.execute(select(table))).all())
                    for table in (CacheResource, CacheVariant, CacheBody, CacheStats)
                ]
            )
    return repr(vars(records))


async def test_a_secret_query_value_reaches_no_cache_table(records):
    setup = Setup(Origin(), {"redaction": redaction(query=["client_secret"])}, records)

    assert await setup.fetch_twice(f"{URL}?client_secret=hunter2-value&x=1") == 1  # cached all the same

    assert "hunter2-value" not in await everything(records)


async def test_the_query_kept_for_display_has_the_secret_replaced(records):
    setup = Setup(Origin(), {"redaction": redaction(query=["client_secret"])}, records)
    await setup.fetch_twice(f"{URL}?client_secret=hunter2-value&x=1")

    (key,) = await records.list_keys()
    ((stored, _),) = await records.get_variants(key)

    assert stored.query == f"client_secret={REDACTED}&x=1"
    assert f"/item?client_secret={REDACTED}&x=1" in stored.head.decode()


async def test_two_query_values_never_share_an_entry(records):
    setup = Setup(Origin(), {"redaction": redaction(query=["client_secret"])}, records)

    async with setup.client:
        await setup.client.get(f"{URL}?client_secret=one")
        await setup.client.get(f"{URL}?client_secret=two")
        await setup.client.get(f"{URL}?client_secret=one")

    assert setup.origin.calls == 2
    assert len(await records.list_keys()) == 2


async def test_a_key_is_the_path_in_clear_and_a_hash_of_the_query(records):
    setup = Setup(Origin(), {"redaction": redaction()}, records)
    async with setup.client:
        await setup.client.get(f"{URL}?x=1")
        await setup.client.get(URL)

    keys = await records.list_keys()

    assert keys[0] == "http://api/item"
    assert keys[1] == f"http://api/item?{hashlib.sha256(b'x=1').hexdigest()}"


async def test_a_url_with_other_query_parameters_is_cached():
    setup = Setup(Origin(), {"redaction": redaction(query=["client_secret"])})

    assert await setup.fetch_twice(f"{URL}?x=1") == 1


async def test_opting_a_name_out_caches_those_responses_again():
    setup = Setup(Origin(**{"set-cookie": "sid=abc"}), {"redaction": redaction(headers_out=["Set-Cookie"])})

    assert await setup.fetch_twice() == 1


async def test_a_header_added_by_a_rule_applies_to_vary():
    setup = Setup(Origin(vary="X-Api-Key"), {"redaction": redaction(headers_in=["X-Api-Key"])})

    assert await setup.fetch_twice() == 2


async def test_skip_markers_keep_the_response_out_of_the_cache():
    for marker in (SKIP_REQUEST_STORAGE, SKIP_RESPONSE_STORAGE):
        setup = Setup(Origin(), {"redaction": redaction(), "markers": frozenset({marker})})

        assert await setup.fetch_twice() == 2, marker
        assert await setup.records.list_keys() == [], marker


async def test_other_markers_do_not_prevent_caching():
    markers = frozenset({"skip-request-body-storage", SKIP_STORAGE})  # skip-storage is also set by load shedding
    setup = Setup(Origin(), {"redaction": redaction(), "markers": markers})

    assert await setup.fetch_twice() == 1


async def test_a_revalidation_cannot_bring_a_redacted_header_into_a_stored_entry():
    setup = Setup(Origin(), {"redaction": redaction()})
    await setup.fetch_twice()
    (key,) = await setup.records.list_keys()
    (entry,) = await setup.storage.get_entries(key)

    def with_cookie(stored):
        headers = Headers({**stored.response.headers, "set-cookie": "sid=abc"})
        return replace(stored, response=replace(stored.response, headers=headers))

    assert await setup.storage.update_entry(entry.id, with_cookie) is None
    assert await setup.records.list_keys() == []

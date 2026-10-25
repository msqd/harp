"""What the cache keeps is redacted like the transaction record, or not kept at all (ADR-0009)."""

from dataclasses import replace

import httpx
from hishel import CacheOptions, Headers, SpecificationPolicy

from harp.models.redaction import REDACTED, Redaction
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.constants import SKIP_REQUEST_STORAGE, SKIP_RESPONSE_STORAGE, SKIP_STORAGE
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://origin.test/item"


class Origin(httpx.AsyncBaseTransport):
    def __init__(self, **headers: str):
        self.headers = {"cache-control": "public, max-age=3600", **headers}
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(200, headers=self.headers, content=b"body")


class Setup:
    def __init__(self, origin: Origin, harp: dict):
        self.origin = origin
        self.blobs = MemoryBlobStorage()
        self.storage = AsyncStorage(self.blobs)
        transport = AsyncCacheTransport(
            next_transport=origin,
            storage=self.storage,
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )

        async def extend(request: httpx.Request) -> None:
            request.extensions["harp"] = {"endpoint": "api", **harp}

        self.client = httpx.AsyncClient(transport=transport, event_hooks={"request": [extend]})

    async def stored_texts(self, content_type: str) -> list[str]:
        return [blob.data.decode() async for blob in self.blobs.iter_blobs(content_type)]

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

    (headers,) = [text for text in await setup.stored_texts("http/headers") if "accept" in text]
    assert f"authorization: {REDACTED}" in headers
    assert "secret-token" not in headers
    assert "accept: */*" in headers


async def test_a_request_outside_a_proxied_transaction_gets_the_default_set():
    setup = Setup(Origin(), {})

    await setup.fetch_twice(authorization="Bearer secret-token")

    assert not any("secret-token" in text for text in await setup.stored_texts("http/headers"))


async def test_a_response_varying_on_a_redacted_header_is_not_cached():
    setup = Setup(Origin(vary="Authorization"), {"redaction": redaction()})

    assert await setup.fetch_twice(authorization="Bearer secret-token") == 2
    assert await setup.stored_texts("cache/meta") == []


async def test_vary_is_matched_whatever_the_case_and_among_other_names():
    setup = Setup(Origin(vary="Accept-Encoding, COOKIE"), {"redaction": redaction()})

    assert await setup.fetch_twice() == 2


async def test_a_response_carrying_a_redacted_response_header_is_not_cached():
    setup = Setup(Origin(**{"set-cookie": "sid=abc"}), {"redaction": redaction()})

    assert await setup.fetch_twice() == 2
    assert await setup.stored_texts("cache/meta") == []


async def test_a_url_carrying_a_redacted_query_parameter_is_not_cached():
    setup = Setup(Origin(), {"redaction": redaction(query=["client_secret"])})

    assert await setup.fetch_twice(f"{URL}?client_secret=abc&x=1") == 2
    assert await setup.stored_texts("cache/meta") == []


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
        assert await setup.stored_texts("cache/meta") == [], marker


async def test_other_markers_do_not_prevent_caching():
    markers = frozenset({"skip-request-body-storage", SKIP_STORAGE})  # skip-storage is also set by load shedding
    setup = Setup(Origin(), {"redaction": redaction(), "markers": markers})

    assert await setup.fetch_twice() == 1


async def test_a_revalidation_cannot_bring_a_redacted_header_into_a_stored_entry():
    setup = Setup(Origin(), {"redaction": redaction()})
    await setup.fetch_twice()
    (blob,) = [blob async for blob in setup.blobs.iter_blobs("cache/meta")]
    (entry,) = await setup.storage.get_entries(blob.id)

    def with_cookie(stored):
        headers = Headers({**stored.response.headers, "set-cookie": "sid=abc"})
        return replace(stored, response=replace(stored.response, headers=headers))

    assert await setup.storage.update_entry(entry.id, with_cookie) is None
    assert await setup.stored_texts("cache/meta") == []

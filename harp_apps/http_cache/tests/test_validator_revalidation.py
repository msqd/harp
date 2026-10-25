"""A response carrying only a validator is kept, and revalidated on every use (#874).

``ETag`` or ``Last-Modified`` without ``Cache-Control`` or ``Expires`` gives the cache nothing to say how long
the response stays fresh, and HARP does not invent it (see ``test_heuristics``). It does not have to throw the
response away either: it keeps it as an entry that is never fresh, so the origin is asked each time with a
conditional request, and a ``304`` saves the body.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.models.redaction import Redaction
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.http_cache.records import MemoryCacheRecords

URL = "http://example.com/resource"


def _http_date(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).strftime("%a, %d %b %Y %H:%M:%S GMT")


class _StorageThatCannotUpdate(AsyncStorage):
    async def update_entry(self, id, new_entry):
        return None


def _client(*, allow_heuristics=False, storage_class=AsyncStorage, allow_stale=False, credentials=()):
    """``credentials`` are the header names a rule declared as credentials on the transaction."""

    async def declare_credentials(request):
        redaction = Redaction()
        redaction.headers.update(credentials)
        request.extensions.setdefault("harp", {})["redaction"] = redaction

    hooks = {"request": [*ENDPOINT_HOOKS["request"], declare_credentials]}
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=storage_class(MemoryCacheRecords(), allow_heuristics=allow_heuristics),
        policy=SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=allow_stale)
        ),
    )
    return AsyncClient(transport=transport, event_hooks=hooks)


def _origin(headers, *, revalidates=True):
    """An origin answering ``headers`` with a numbered body, or ``304`` to a request carrying a matching validator."""
    seen = []

    def respond(request):
        seen.append(request)
        validators = {request.headers.get("if-none-match"), request.headers.get("if-modified-since")} - {None}
        if revalidates and validators & {headers.get("etag"), headers.get("last-modified")}:
            return Response(304)
        return Response(200, content=f"body-{len(seen)}".encode(), headers=headers)

    respx.get(URL).mock(side_effect=respond)
    return seen


@pytest.mark.asyncio
class TestValidatorOnlyResponses:
    @respx.mock
    async def test_etag_is_revalidated_and_a_304_serves_the_stored_body(self):
        seen = _origin({"etag": '"v1"'})

        async with _client() as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert [r.headers.get("if-none-match") for r in seen] == [None, '"v1"']
        assert (first.content, second.content) == (b"body-1", b"body-1")

    @respx.mock
    async def test_last_modified_is_revalidated_and_a_304_serves_the_stored_body(self):
        last_modified = _http_date(timedelta(days=-30))
        seen = _origin({"last-modified": last_modified})

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)

        assert [r.headers.get("if-modified-since") for r in seen] == [None, last_modified]
        assert second.content == b"body-1"

    @respx.mock
    async def test_a_200_to_the_conditional_request_serves_the_new_body(self):
        seen = _origin({"etag": '"v1"'}, revalidates=False)

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)

        assert seen[1].headers.get("if-none-match") == '"v1"'
        assert second.content == b"body-2"

    @respx.mock
    async def test_the_entry_is_never_served_without_the_origin_confirming_it(self):
        """Every use asks the origin, whatever the age of the entry: a heuristic would have made later ones free."""
        seen = _origin({"last-modified": _http_date(timedelta(days=-365))})

        async with _client() as client:
            for _ in range(4):
                response = await client.get(URL)

        assert len(seen) == 4
        assert response.content == b"body-1"

    @respx.mock
    async def test_with_the_origin_down_the_request_fails(self):
        calls = []

        def respond(request):
            calls.append(request)
            if len(calls) > 1:
                raise httpx.ConnectError("down")
            return Response(200, content=b"body-1", headers={"etag": '"v1"'})

        respx.get(URL).mock(side_effect=respond)

        async with _client() as client:
            await client.get(URL)
            with pytest.raises(httpx.ConnectError):
                await client.get(URL)

    @respx.mock
    async def test_a_304_without_date_does_not_leak_the_marker_to_the_client(self):
        """The client sees the ``Date`` the origin gave the stored response, not the one that keeps it stale."""
        date = _http_date(timedelta(hours=-1))
        _origin({"etag": '"v1"', "date": date})

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)
            third = await client.get(URL)

        assert second.headers["date"] == date
        assert third.headers["date"] == date
        assert "x-harp-original-date" not in third.headers

    @respx.mock
    async def test_the_marker_does_not_leak_when_the_stored_entry_cannot_be_refreshed(self):
        date = _http_date(timedelta(hours=-1))
        _origin({"etag": '"v1"', "date": date})

        async with _client(storage_class=_StorageThatCannotUpdate) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert second.headers["date"] == date
        assert "x-harp-original-date" not in second.headers

    @respx.mock
    async def test_neither_validator_nor_expiry_is_not_retained(self):
        seen = _origin({})

        async with _client() as client:
            await client.get(URL)
            await client.get(URL)

        assert [r.headers.get("if-none-match") for r in seen] == [None, None]
        assert [r.headers.get("if-modified-since") for r in seen] == [None, None]

    @respx.mock
    async def test_no_cache_with_a_validator_is_not_retained(self):
        """hishel never reuses a ``no-cache`` entry, not even by revalidating it: keeping it would store for nothing."""
        _origin({"etag": '"v1"', "cache-control": "no-cache"})

        async with _client() as client:
            await client.get(URL)
            storage = client._transport.storage
            assert await storage.get_entries(await client._transport._key_for(httpx.URL(URL), "test-endpoint")) == []

    @respx.mock
    async def test_an_explicit_expiry_still_serves_without_asking(self):
        seen = _origin({"etag": '"v1"', "cache-control": "max-age=3600"})

        async with _client() as client:
            await client.get(URL)
            await client.get(URL)

        assert len(seen) == 1

    @respx.mock
    async def test_allow_heuristics_still_opts_into_heuristic_freshness(self):
        seen = _origin({"last-modified": _http_date(timedelta(days=-30))})

        async with _client(allow_heuristics=True) as client:
            await client.get(URL)
            await client.get(URL)

        assert len(seen) == 1


def _per_caller_origin(kind, validator, *, response_headers=None, on_200=True):
    """``/me`` answered per ``X-Api-Key``; a conditional request is answered ``304`` as an origin that only compares validators does."""
    seen = []

    def respond(request):
        who = (
            request.headers.get("x-api-key")
            or request.headers.get("authorization")
            or request.headers.get("cookie", "").removeprefix("session=")
        )
        seen.append(who)
        conditional = (
            request.headers.get("if-modified-since")
            if kind == "last-modified"
            else request.headers.get("if-none-match")
        )
        if conditional == validator:
            return Response(304, headers=response_headers or {})
        return Response(
            200,
            content=f"for-{who}".encode(),
            headers={kind: validator, **((response_headers or {}) if on_200 else {})},
        )

    respx.get(URL).mock(side_effect=respond)
    return seen


CALLER_HEADERS = [
    pytest.param({"x-api-key": "alice"}, {"x-api-key": "bob"}, ("x-api-key",), id="declared-x-api-key"),
    pytest.param({"cookie": "session=alice"}, {"cookie": "session=bob"}, (), id="cookie"),
    pytest.param({"authorization": "alice"}, {"authorization": "bob"}, (), id="authorization"),
]
VALIDATORS = [
    pytest.param("last-modified", _http_date(timedelta(days=-30)), id="last-modified"),
    pytest.param("etag", 'W/"1"', id="weak-etag"),
]


@pytest.mark.asyncio
class TestCredentialedRequestsAreNotRetained:
    @pytest.mark.parametrize(("alice", "bob", "declared"), CALLER_HEADERS)
    @pytest.mark.parametrize(("kind", "validator"), VALIDATORS)
    @respx.mock
    async def test_a_callers_response_is_never_handed_to_another(self, alice, bob, declared, kind, validator):
        """A conditional request proves the validator still matches, not that the body is the caller's."""
        seen = _per_caller_origin(kind, validator)

        async with _client(credentials=declared) as client:
            await client.get(URL, headers=alice)
            second = await client.get(URL, headers=bob)

        assert second.content == b"for-" + bob[next(iter(bob))].removeprefix("session=").encode()
        assert len(seen) == 2

    @respx.mock
    async def test_a_304_bringing_a_max_age_does_not_make_it_servable_to_further_callers(self):
        validator = _http_date(timedelta(days=-30))
        _per_caller_origin("last-modified", validator, response_headers={"cache-control": "max-age=600"}, on_200=False)

        async with _client(credentials=("x-api-key",)) as client:
            for caller in ("alice", "bob", "carol"):
                response = await client.get(URL, headers={"x-api-key": caller})

        assert response.content == b"for-carol"

    @respx.mock
    async def test_a_response_setting_a_cookie_is_not_retained(self):
        validator = _http_date(timedelta(days=-30))
        _per_caller_origin("last-modified", validator, response_headers={"set-cookie": "a=1"})

        async with _client() as client:
            await client.get(URL)
            storage = client._transport.storage
            assert await storage.get_entries(await client._transport._key_for(httpx.URL(URL), "test-endpoint")) == []

    @pytest.mark.parametrize(("kind", "validator"), VALIDATORS)
    @respx.mock
    async def test_without_any_credential_the_response_is_retained_and_revalidated(self, kind, validator):
        seen = _per_caller_origin(kind, validator)

        async with _client(credentials=("x-api-key",)) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert second.content == b"for-"
        assert len(seen) == 2
        assert second.status_code == 200


@pytest.mark.asyncio
class TestStaleServing:
    @respx.mock
    async def test_the_age_of_an_entry_served_stale_comes_from_its_real_date(self):
        date = _http_date(timedelta(hours=-1))
        _origin({"etag": '"v1"', "date": date})

        async with _client(allow_stale=True) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert second.headers["date"] == date
        assert 3590 <= int(second.headers["age"]) <= 3700


@pytest.mark.asyncio
class TestHeuristicEntriesAfterTurningHeuristicsOff:
    @respx.mock
    async def test_an_entry_stored_with_heuristics_on_is_revalidated_once_they_are_off(self):
        seen = _origin({"last-modified": _http_date(timedelta(days=-30))})
        storage = AsyncStorage(MemoryCacheRecords(), allow_heuristics=True)

        async with _client(storage_class=lambda records, allow_heuristics: storage, allow_heuristics=True) as client:
            await client.get(URL)
            await client.get(URL)
        assert len(seen) == 1

        storage._allow_heuristics = False
        async with _client(storage_class=lambda records, allow_heuristics: storage) as client:
            await client.get(URL)
        assert len(seen) == 2

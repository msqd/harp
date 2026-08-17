"""Test what actually crosses the wire when a stored response goes stale (RFC 9111 §4.3).

The other files in this directory assert what the cache stores. This one asserts what the
**origin sees**, because that is where both defects in #906 are visible and neither is
visible from cache internals:

- a revalidation that carries no validator looks identical, from the storage side, to one
  that carries one. Only the origin can tell you the body was transferred again.
- an entry that is never freshened looks identical, from a single request, to one that is.
  Only a third request can tell you the revalidation converged.

Every origin response here sets ``Date``. Without it hishel's ``get_age`` returns 0 and the
entry never ages, so the staleness boundary these tests exist to cross would never arrive
and every one of them would pass while measuring nothing.
"""

import time
from typing import Optional

import pytest
import respx
from httpx import Response

from harp_apps.http_cache.tests.rfc9111.conftest import http_date

# Origins are asked for a resource that goes stale almost immediately, so the boundary is
# crossed by a short real sleep rather than by clock mocking.
MAX_AGE = 1
PAST_BOUNDARY = MAX_AGE + 0.5


class RecordingOrigin:
    """An origin that answers 304 to a matching validator, and records what it was asked.

    Counting requests here rather than inspecting the cache is deliberate: it is the only
    vantage point from which "the body was transferred again" is distinguishable from "the
    body was not".
    """

    def __init__(self, *, etag: Optional[str] = None, last_modified: Optional[str] = None, body=b"payload"):
        self.etag = etag
        self.last_modified = last_modified
        self.body = body
        self.requests = []

    def _headers(self):
        headers = {
            "content-type": "text/plain",
            "cache-control": f"max-age={MAX_AGE}",
            "date": http_date(),
        }
        if self.etag is not None:
            headers["etag"] = self.etag
        if self.last_modified is not None:
            headers["last-modified"] = self.last_modified
        return headers

    def __call__(self, request):
        self.requests.append(request)
        if self.etag is not None and request.headers.get("if-none-match") == self.etag:
            return Response(304, headers=self._headers())
        if self.last_modified is not None and request.headers.get("if-modified-since") == self.last_modified:
            return Response(304, headers=self._headers())
        return Response(200, content=self.body, headers=self._headers())

    @property
    def count(self):
        return len(self.requests)

    def conditional_headers(self, index):
        headers = self.requests[index].headers
        return {name: headers[name] for name in ("if-none-match", "if-modified-since") if name in headers}

    def install(self, url="http://example.com/resource"):
        return respx.get(url).mock(side_effect=self)


@pytest.mark.asyncio
class TestRevalidationCarriesAValidator:
    """The revalidation request must carry the validator the stored response provided."""

    @respx.mock
    async def test_strong_etag_revalidation_sends_if_none_match_rfc9111_4_3_1(self, cached_client):
        """RFC 9111 §4.3.1: a cache revalidating a stored response sends its ETag.

        Quote from RFC:
        > When generating a conditional request for validation, a cache [...] MUST send the
        > relevant entity tags [...] using the If-None-Match header field.

        Without the validator the origin has nothing to compare against and must answer 200
        with the whole body, which is the wasted transfer this test exists to detect.
        """
        origin = RecordingOrigin(etag='"strong-v1"')
        origin.install()

        first = await cached_client.get("http://example.com/resource")
        assert first.content == b"payload"
        assert origin.count == 1

        time.sleep(PAST_BOUNDARY)
        second = await cached_client.get("http://example.com/resource")

        assert origin.count == 2, "the stale entry was not revalidated at all"
        assert origin.conditional_headers(1) == {"if-none-match": '"strong-v1"'}
        assert origin.requests[1].method == "GET"

        # The client still gets the full representation, reconstructed from the stored body.
        assert second.status_code == 200
        assert second.content == b"payload"

    @respx.mock
    async def test_weak_etag_revalidation_sends_if_none_match_rfc9111_4_3_1(self, cached_client):
        """RFC 9111 §4.3.1: a weak ETag is a validator for revalidation just as a strong one is."""
        origin = RecordingOrigin(etag='W/"weak-v1"')
        origin.install()

        await cached_client.get("http://example.com/resource")
        time.sleep(PAST_BOUNDARY)
        second = await cached_client.get("http://example.com/resource")

        assert origin.count == 2
        assert origin.conditional_headers(1) == {"if-none-match": 'W/"weak-v1"'}
        assert second.status_code == 200
        assert second.content == b"payload"

    @respx.mock
    async def test_last_modified_revalidation_sends_if_modified_since_rfc9111_4_3_1(self, cached_client):
        """RFC 9111 §4.3.1: with no ETag, ``Last-Modified`` is sent as ``If-Modified-Since``."""
        last_modified = http_date()
        origin = RecordingOrigin(last_modified=last_modified)
        origin.install()

        await cached_client.get("http://example.com/resource")
        time.sleep(PAST_BOUNDARY)
        second = await cached_client.get("http://example.com/resource")

        assert origin.count == 2
        assert origin.conditional_headers(1) == {"if-modified-since": last_modified}
        assert second.status_code == 200
        assert second.content == b"payload"

    @respx.mock
    async def test_revalidation_without_a_validator_is_unconditional_rfc9111_4_3_1(self, cached_client):
        """An entry with no validator has nothing to send, and must not regress.

        This is the control for the three tests above: it proves they are detecting a
        validator that is present and expected, not merely a request that happened to be made.
        """
        origin = RecordingOrigin()
        origin.install()

        await cached_client.get("http://example.com/resource")
        time.sleep(PAST_BOUNDARY)
        second = await cached_client.get("http://example.com/resource")

        assert origin.count == 2
        assert origin.conditional_headers(1) == {}
        assert second.status_code == 200
        assert second.content == b"payload"


@pytest.mark.asyncio
class TestRevalidationConverges:
    """A 304 must freshen the stored entry, or the cache revalidates forever."""

    @respx.mock
    async def test_304_freshens_the_entry_so_the_next_request_is_a_hit_rfc9111_4_3_4(self, any_cached_client):
        """RFC 9111 §4.3.4: a 304 updates the stored response, which restarts its freshness.

        Quote from RFC:
        > the cache MUST update its header fields with the header fields provided in the 304
        > (Not Modified) response.

        The third request is the whole point. Requests one and two look identical whether or
        not the entry was freshened; only a request inside the *new* freshness lifetime can
        tell "revalidated once and converged" from "revalidates every single time".
        """
        origin = RecordingOrigin(etag='"converge-v1"')
        origin.install()

        await any_cached_client.get("http://example.com/resource")
        time.sleep(PAST_BOUNDARY)
        second = await any_cached_client.get("http://example.com/resource")

        assert origin.count == 2, "the stale entry was not revalidated"
        assert second.status_code == 200
        assert second.content == b"payload"

        third = await any_cached_client.get("http://example.com/resource")

        assert origin.count == 2, "the 304 did not freshen the entry, so the cache revalidates forever"
        assert third.status_code == 200
        assert third.content == b"payload"

    @respx.mock
    async def test_a_freshened_entry_goes_stale_again_at_the_new_boundary_rfc9111_4_2(self, any_cached_client):
        """Freshening restarts the freshness lifetime, it does not make the entry permanent.

        Paired with the test above so "no origin request" cannot be read as "the cache stopped
        revalidating altogether", which would be a different and worse defect wearing the same
        green tick.
        """
        origin = RecordingOrigin(etag='"expiry-v1"')
        origin.install()

        await any_cached_client.get("http://example.com/resource")
        time.sleep(PAST_BOUNDARY)
        await any_cached_client.get("http://example.com/resource")
        assert origin.count == 2

        time.sleep(PAST_BOUNDARY)
        await any_cached_client.get("http://example.com/resource")

        assert origin.count == 3, "the freshened entry never went stale again"
        assert origin.conditional_headers(2) == {"if-none-match": '"expiry-v1"'}

    @respx.mock
    async def test_a_200_on_revalidation_replaces_the_entry_rfc9111_4_3_3(self, any_cached_client):
        """When the origin answers 200 instead of 304, the new representation is what is served."""
        origin = RecordingOrigin(etag='"changed-v1"', body=b"first")
        origin.install()

        first = await any_cached_client.get("http://example.com/resource")
        assert first.content == b"first"

        # The representation changes underneath the cache, so the stored validator no longer matches.
        origin.etag = '"changed-v2"'
        origin.body = b"second"

        time.sleep(PAST_BOUNDARY)
        second = await any_cached_client.get("http://example.com/resource")

        assert origin.count == 2
        assert origin.conditional_headers(1) == {"if-none-match": '"changed-v1"'}
        assert second.status_code == 200
        assert second.content == b"second"

        third = await any_cached_client.get("http://example.com/resource")
        assert origin.count == 2, "the replacement was not stored"
        assert third.content == b"second"

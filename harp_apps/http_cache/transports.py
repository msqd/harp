import time
from dataclasses import replace

import httpx
from hishel import Request, Response
from hishel._async_httpx import _httpx_to_internal as _hishel_httpx_to_internal
from hishel._async_httpx import _IteratorStream
from hishel._core._spec import parse_date
from hishel._core.models import ResponseMetadata
from hishel.httpx import AsyncCacheTransport as HishelAsyncCacheTransport

from harp import get_logger
from harp.http.utils import hop_by_hop_names, parse_cache_control
from harp.utils.bytes import HEADER_ENCODING, ensure_bytes, header_bytes
from harp_apps.http_cache.coalescing import DEFAULT_TIMEOUT, Coalescer
from harp_apps.http_cache.models import WrappedRequest
from harp_apps.http_cache.storages import MARKERS_METADATA, MAX_BODY_SIZE_METADATA, REDACTION_METADATA
from harp_apps.http_cache.streams import ClosableByteStream, UpstreamBody

logger = get_logger(__name__)


def _httpx_to_internal(value):
    """hishel reads headers as text, and httpx guesses how to decode them: obs-text must not be guessed.

    hishel also gathers a response body into 128 KiB pieces, which holds back what arrives first until the piece
    fills: the body is passed on as it arrives instead."""
    value.headers.encoding = HEADER_ENCODING
    internal = _hishel_httpx_to_internal(value)
    if isinstance(value, httpx.Response) and not value.is_stream_consumed:
        internal = replace(internal, stream=UpstreamBody(value))
    return internal


def _internal_to_httpx(value):
    """The reverse, handing httpx bytes: given text it would insist on ascii, and refuse obs-text.

    Closing the httpx response closes its body, so an upstream body the client stops reading is released at once."""
    headers = [(header_bytes(name), header_bytes(val)) for name, val in value.headers.items()]
    if isinstance(value, Response):
        stream = ClosableByteStream(value.stream)
        return httpx.Response(value.status_code, headers=headers, stream=stream, extensions=value.metadata)
    stream = _IteratorStream(value._aiter_stream())
    return httpx.Request(value.method, value.url, headers=headers, stream=stream, extensions=value.metadata)


# An HTTP date in the past, standing for "already expired".
_ALREADY_EXPIRED = "Thu, 01 Jan 1970 00:00:00 GMT"
# Carries the upstream's malformed Expires through the cache, so the client can be given it back.
_ORIGINAL_EXPIRES = "x-harp-original-expires"


def _expire_malformed_expires(response: Response) -> None:
    """RFC 9111 §5.3: an invalid ``Expires`` value means "already expired".

    hishel raises on a value it cannot parse, which would answer the client a 500 for an upstream's mistake.
    The cache is told the response is already expired; the original value is kept aside, because a proxy does
    not change what the client receives (see :func:`_restore_original_expires`).
    """
    if "expires" in response.headers and parse_date(response.headers["expires"]) is None:
        response.headers[_ORIGINAL_EXPIRES] = response.headers["expires"]
        del response.headers["expires"]  # assigning would add a value next to the malformed one
        response.headers["expires"] = _ALREADY_EXPIRED


def _restore_original_expires(response: httpx.Response) -> None:
    """Give the client the upstream's own ``Expires``, whether the response is fresh, cached or revalidated."""
    if _ORIGINAL_EXPIRES in response.headers:
        original = response.headers[_ORIGINAL_EXPIRES]
        del response.headers[_ORIGINAL_EXPIRES]
        response.headers["expires"] = original


def _endpoint_name(request: httpx.Request) -> str:
    endpoint_name = request.extensions.get("harp", {}).get("endpoint")
    if not endpoint_name:
        raise ValueError(
            f"The cache transport requires an endpoint name in request.extensions['harp']['endpoint'] "
            f"(url={request.url}); without it, unrelated requests would share one cache namespace."
        )
    return endpoint_name


def _max_recorded_body_size(request: httpx.Request) -> int | None:
    """The proxy's recording cap for this request, if it set one: the cache stores no body larger."""
    return request.extensions.get("harp", {}).get("max_recorded_body_size")


def _cache_url(url: httpx.URL, endpoint_name: str) -> str:
    # We change the internal request url to use a host containing our proxy name, to avoid multiple cache for load balanced endpoints.
    return str(url.copy_with(netloc=ensure_bytes(endpoint_name), host=endpoint_name))


def _rewrite_request_url(request: httpx.Request) -> str:
    return _cache_url(request.url, _endpoint_name(request))


# Methods that RFC 9110 §9.2.1 defines as safe: they never invalidate anything.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _invalidated_urls(request: httpx.Request, response: httpx.Response) -> list[httpx.URL]:
    """The URIs a successful unsafe request invalidates, per RFC 9111 §4.4.

    That is the target URI, plus the ``Location`` and ``Content-Location`` URIs when they are on the
    same host as the target (the host check stops an origin from invalidating another site's entries).
    """
    urls = [request.url]
    for name in ("location", "content-location"):
        value = response.headers.get(name)
        if not value:
            continue
        try:
            url = request.url.join(value)
        except httpx.InvalidURL:
            logger.debug(f"Ignoring unparsable {name} header for invalidation: value={value!r}")
            continue
        if (url.host, url.port, url.scheme) == (request.url.host, request.url.port, request.url.scheme):
            urls.append(url)
    return [url.copy_with(fragment=None) for url in urls]


def _forbids_storage(request: httpx.Request) -> bool:
    """Whether the client asked, per RFC 9111 §5.2.1.5, that nothing about this exchange be cached.

    hishel 1.x decides cacheability from the response alone (RFC 9111 §3), and dropped the
    request-side check its 0.1.x controller used to make. So the request directive has to be read
    here or it is not read at all.
    """
    return bool(parse_cache_control(request.headers.get("cache-control")).no_store)


#: Methods whose concurrent misses are coalesced: the ones a shared cache answers from a stored response.
COALESCED_METHODS = frozenset({"GET", "HEAD"})


class AsyncCacheTransport(HishelAsyncCacheTransport):
    def __init__(self, *args, coalescing_timeout: float = DEFAULT_TIMEOUT, **kwargs):
        """``coalescing_timeout`` bounds, in seconds, how long a request waits for the fetch it shares with others."""
        super().__init__(*args, **kwargs)
        self._coalescer = Coalescer(coalescing_timeout)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Wraps the request to use a rewritten url (for cache key handling)."""
        internal_request = _httpx_to_internal(request)
        url = _rewrite_request_url(request)

        logger.debug(
            f"Handling async request with rewritten URL for caching: original_url={request.url}, rewritten_url={url}"
        )

        wrapped_request = WrappedRequest(
            internal_request,
            url=url,
            metadata={
                **internal_request.metadata,
                MAX_BODY_SIZE_METADATA: _max_recorded_body_size(request),
                REDACTION_METADATA: request.extensions.get("harp", {}).get("redaction"),
                MARKERS_METADATA: request.extensions.get("harp", {}).get("markers"),
            },
        )

        if _forbids_storage(request):
            logger.debug(f"Bypassing cache, the request forbids storage (RFC 9111 §5.2.1.5): url={request.url}")
            internal_response = await self._send_without_caching(wrapped_request)
        else:
            internal_response = await self._handle_cacheable_request(wrapped_request)

        response = _internal_to_httpx(internal_response)
        _restore_original_expires(response)
        if request.method not in SAFE_METHODS and response.status_code < 400:
            await self._invalidate(request, response)
        return response

    async def _handle_cacheable_request(self, request: WrappedRequest) -> Response:
        """Concurrent misses for one variant of a resource share one origin fetch (#947)."""
        if request.method not in COALESCED_METHODS:
            return await self._cache_proxy.handle_request(request)
        key = await self._cache_proxy._get_key_for_request(request)
        return await self._coalescer.run(key, request, self._cache_proxy.handle_request)

    async def _invalidate(self, request: httpx.Request, response: httpx.Response) -> None:
        """Drop the stored entries for the resources a successful unsafe request has changed (RFC 9111 §4.4)."""
        endpoint_name = _endpoint_name(request)
        for url in _invalidated_urls(request, response):
            key = await self._cache_proxy._get_key_for_request(
                Request(method="GET", url=_cache_url(url, endpoint_name))
            )
            for entry in await self.storage.get_entries(key):
                await self.storage.remove_entry(entry.id)
            logger.debug(f"Cache invalidated by {request.method} {request.url}: url={url}")

    async def _send_without_caching(self, request: WrappedRequest) -> Response:
        """Go upstream without involving the cache at all, and report the result as a plain miss.

        Deliberately routed through :meth:`request_sender` rather than ``next_transport``: that is
        where the upstream's connection-specific fields are dropped, and it is the one place the
        rule lives. Sending straight to ``next_transport`` here would leak them to the client for
        no-store requests only, which is the path nobody would think to re-probe.

        The metadata below is the shape hishel writes when it decides a response cannot be stored.
        Without it the response carries no ``hishel_from_cache`` key at all, and the proxy adapter
        emits no ``X-Cache`` header rather than ``MISS``.
        """
        response = await self.request_sender(request)
        response.metadata.update(  # type: ignore[union-attr]
            ResponseMetadata(
                hishel_created_at=time.time(),
                hishel_from_cache=False,
                hishel_revalidated=False,
                hishel_stored=False,
            )
        )
        return response

    async def request_sender(self, request: WrappedRequest) -> Response:
        """Unwraps the request before sending it, and drops the upstream's connection-specific fields.

        This is the last point at which ``Connection`` can still be read. Further down, hishel
        removes ``Connection`` itself and leaves the fields it named behind, so by the time the
        proxy controller sees a cached response there is nothing left to identify them by and
        RFC 9110 §7.6.1 cannot be applied. Dropping them here also means they are never written to
        the cache, which is what RFC 9111 §3.1 asks for.

        ``content-length`` is deliberately kept: it describes the body being stored, and the
        controller drops it on the way out to the client anyway.
        """
        httpx_response = await self.next_transport.handle_async_request(_internal_to_httpx(request.unwrap()))
        if httpx_response.status_code == 304:
            await httpx_response.aread()  # never leave a stream unconsumed
        response = _httpx_to_internal(httpx_response)
        dropped = hop_by_hop_names(response.headers) - {"content-length"}
        for name in [name for name in response.headers if name.lower() in dropped]:
            del response.headers[name]
        _expire_malformed_expires(response)
        return response

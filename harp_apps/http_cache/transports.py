import hashlib
import time
from ipaddress import IPv6Address, ip_address
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
from harp_apps.http_cache.settings import PurgeSettings
from harp_apps.http_cache.storages import (
    REQUEST_URL,
    MARKERS_METADATA,
    FETCH_STAMP,
    MAX_BODY_SIZE_METADATA,
    REDACTION_METADATA,
    restore_date,
)
from harp_apps.http_cache.records import BanMode
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
            f"(url={request.url.copy_with(query=None)}); without it, unrelated requests would share one cache namespace."
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


def _peer_address(request: httpx.Request):
    """The address of the peer HARP is talking to, as the proxy saw it; ``None`` when unknown or unparsable."""
    try:
        address = ip_address(request.extensions.get("harp", {}).get("client_ip"))
    except ValueError:
        return None
    return address.ipv4_mapped or address if isinstance(address, IPv6Address) else address


#: Methods whose concurrent misses are coalesced: the ones a shared cache answers from a stored response.
COALESCED_METHODS = frozenset({"GET", "HEAD"})


class AsyncCacheTransport(HishelAsyncCacheTransport):
    def __init__(
        self, *args, coalescing_timeout: float = DEFAULT_TIMEOUT, purge: PurgeSettings | None = None, **kwargs
    ):
        """``coalescing_timeout`` bounds, in seconds, how long a request waits for the fetch it shares with others.

        ``purge`` opts into answering ``PURGE`` requests (#801); without it they are proxied like any other."""
        super().__init__(*args, **kwargs)
        self._purge = purge or PurgeSettings()
        self._coalescer = Coalescer(coalescing_timeout)
        self._hishel_key_for_request = self._cache_proxy._get_key_for_request
        self._cache_proxy._get_key_for_request = self._get_key_for_request

    async def _get_key_for_request(self, request: Request) -> str:
        """The cache key: endpoint and path in clear, then a hash of the whole query string.

        hishel hashes the url, which hides what the cache stores: the store orders its records by key to list them per
        endpoint and per path, and a path prefix is a range of keys (ADR-0014). The query stays out of the key but for
        its hash, as it may hold credentials (ADR-0009): two different values never share an entry. A request keyed by
        its body has the hash of its body in the hash.
        """
        REQUEST_URL.set(str(request.url))
        url = httpx.URL(request.url)
        path, _, query = url.raw_path.decode("ascii").partition("?")
        key = f"{url.scheme}://{url.netloc.decode('utf-8')}{path}"
        if self._cache_proxy.policy.use_body_key or request.metadata.get("hishel_body_key"):
            query += "\0" + await self._hishel_key_for_request(request)
        return f"{key}?{hashlib.sha256(query.encode()).hexdigest()}" if query else key

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Wraps the request to use a rewritten url (for cache key handling)."""
        if request.method == "PURGE" and self._purge.enabled:
            return await self._handle_purge(request)

        internal_request = _httpx_to_internal(request)
        url = _rewrite_request_url(request)

        logger.debug(
            f"Handling async request with rewritten URL for caching: original_url={request.url.copy_with(query=None)}, rewritten_url={url.partition('?')[0]}"
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
        FETCH_STAMP.set(None)  # this request has not been to the origin yet, see request_sender

        if _forbids_storage(request):
            logger.debug(
                f"Bypassing cache, the request forbids storage (RFC 9111 §5.2.1.5): url={request.url.copy_with(query=None)}"
            )
            internal_response = await self._send_without_caching(wrapped_request)
        else:
            internal_response = await self._handle_cacheable_request(wrapped_request)

        response = _internal_to_httpx(internal_response)
        _restore_original_expires(response)
        restore_date(response.headers)
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
            await self.storage.invalidate(await self._key_for(url, endpoint_name), mode=BanMode.HARD)
            logger.debug(
                f"Cache invalidated by {request.method} {request.url.copy_with(query=None)}: url={url.copy_with(query=None)}"
            )

    async def _key_for(self, url: httpx.URL, endpoint_name: str) -> str:
        return await self._cache_proxy._get_key_for_request(Request(method="GET", url=_cache_url(url, endpoint_name)))

    async def _handle_purge(self, request: httpx.Request) -> httpx.Response:
        """Answer ``PURGE`` here, never upstream: ``403`` for a peer out of the allow-list, else ``200`` or ``404``."""
        peer = _peer_address(request)
        if peer is None or not any(peer in network for network in self._purge.allow):
            logger.warning(
                f"Cache purge refused, peer is not allowed: peer={peer} url={request.url.copy_with(query=None)}"
            )
            return httpx.Response(403, text="Forbidden")
        key = await self._key_for(request.url.copy_with(fragment=None), _endpoint_name(request))
        if not await self.storage.get_entries(key):
            return httpx.Response(404, text="Not in cache")
        await self.storage.invalidate(key, mode=BanMode.HARD)
        logger.info(f"Cache purged: url={request.url.copy_with(query=None)}")
        return httpx.Response(200, text="Purged")

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

        The invalidation counter is read just before going upstream, for the response (or the confirmation of a stored
        one) not to outlive an invalidation that lands while the origin answers: see :data:`FETCH_STAMP`.
        """
        FETCH_STAMP.set(await self.storage.stamp())
        httpx_response = await self.next_transport.handle_async_request(_internal_to_httpx(request.unwrap()))
        if httpx_response.status_code == 304:
            await httpx_response.aread()  # never leave a stream unconsumed
        response = _httpx_to_internal(httpx_response)
        dropped = hop_by_hop_names(response.headers) - {"content-length"}
        for name in [name for name in response.headers if name.lower() in dropped]:
            del response.headers[name]
        _expire_malformed_expires(response)
        return response

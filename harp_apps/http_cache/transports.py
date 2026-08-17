import time

import httpx
from hishel import Response
from hishel._async_httpx import (
    _httpx_to_internal,
    _internal_to_httpx,
)
from hishel._core.models import ResponseMetadata
from hishel.httpx import AsyncCacheTransport as HishelAsyncCacheTransport

from harp import get_logger
from harp.http.utils import hop_by_hop_names, parse_cache_control
from harp.utils.bytes import ensure_bytes
from harp_apps.http_cache.models import WrappedRequest

logger = get_logger(__name__)


def _rewrite_request_url(request: httpx.Request) -> str:
    # We change the internal request url to use a host containing our proxy name, to avoid multiple cache for load balanced endpoints.
    endpoint_name = request.extensions.get("harp", {}).get("endpoint", "__upstream__")
    return str(request.url.copy_with(netloc=ensure_bytes(endpoint_name), host=endpoint_name))


def _forbids_storage(request: httpx.Request) -> bool:
    """Whether the client asked, per RFC 9111 §5.2.1.5, that nothing about this exchange be cached.

    hishel 1.x decides cacheability from the response alone (RFC 9111 §3), and dropped the
    request-side check its 0.1.x controller used to make. So the request directive has to be read
    here or it is not read at all.
    """
    return bool(parse_cache_control(request.headers.get("cache-control")).no_store)


class AsyncCacheTransport(HishelAsyncCacheTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Wraps the request to use a rewritten url (for cache key handling)."""
        internal_request = _httpx_to_internal(request)
        url = _rewrite_request_url(request)

        logger.debug(
            f"Handling async request with rewritten URL for caching: original_url={request.url}, rewritten_url={url}"
        )

        wrapped_request = WrappedRequest(internal_request, url=url)

        if _forbids_storage(request):
            logger.debug(f"Bypassing cache, the request forbids storage (RFC 9111 §5.2.1.5): url={request.url}")
            return _internal_to_httpx(await self._send_without_caching(wrapped_request))

        internal_response = await self._cache_proxy.handle_request(wrapped_request)
        return _internal_to_httpx(internal_response)

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
        response = await super().request_sender(request.unwrap())
        dropped = hop_by_hop_names(response.headers) - {"content-length"}
        for name in [name for name in response.headers if name.lower() in dropped]:
            del response.headers[name]
        return response

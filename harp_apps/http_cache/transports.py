import httpx
from hishel import Response
from hishel._async_httpx import (
    _httpx_to_internal,
    _internal_to_httpx,
)
from hishel.httpx import AsyncCacheTransport as HishelAsyncCacheTransport

from harp import get_logger
from harp.http.utils import hop_by_hop_names
from harp.utils.bytes import ensure_bytes
from harp_apps.http_cache.models import WrappedRequest

logger = get_logger(__name__)


def _rewrite_request_url(request: httpx.Request) -> str:
    # We change the internal request url to use a host containing our proxy name, to avoid multiple cache for load balanced endpoints.
    endpoint_name = request.extensions.get("harp", {}).get("endpoint", "__upstream__")
    return str(request.url.copy_with(netloc=ensure_bytes(endpoint_name), host=endpoint_name))


class AsyncCacheTransport(HishelAsyncCacheTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Wraps the request to use a rewritten url (for cache key handling)."""
        internal_request = _httpx_to_internal(request)
        url = _rewrite_request_url(request)

        logger.debug(
            f"Handling async request with rewritten URL for caching: original_url={request.url}, rewritten_url={url}"
        )

        internal_response = await self._cache_proxy.handle_request(WrappedRequest(internal_request, url=url))
        return _internal_to_httpx(internal_response)

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

import httpx
from hishel import Response
from hishel._async_httpx import (
    _httpx_to_internal,
    _internal_to_httpx,
)
from hishel.httpx import AsyncCacheTransport as HishelAsyncCacheTransport

from harp import get_logger
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
        """Unwraps the request before sending it."""
        return await super().request_sender(request.unwrap())

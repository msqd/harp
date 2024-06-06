from hishel import HEURISTICALLY_CACHEABLE_STATUS_CODES, AsyncCacheTransport, Controller
from httpx import AsyncClient, AsyncHTTPTransport

from harp.config import Application
from harp.config.events import FactoryBindEvent
from harp.settings import DEFAULT_TIMEOUT


class HttpClientApplication(Application):
    async def on_bind(self, event: FactoryBindEvent):
        # todo timeout config ?
        # todo lazy build ?
        transport = AsyncHTTPTransport()
        cache_transport = AsyncCacheTransport(
            transport=transport,
            controller=Controller(
                allow_heuristics=True,
                cacheable_status_codes=HEURISTICALLY_CACHEABLE_STATUS_CODES,
                allow_stale=True,
            ),
        )
        event.container.add_instance(
            AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                transport=cache_transport,
            )
        )

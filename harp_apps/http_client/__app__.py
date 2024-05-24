from hishel import AsyncCacheTransport
from httpx import AsyncClient, AsyncHTTPTransport

from harp.config import Application
from harp.config.events import FactoryBindEvent
from harp.settings import DEFAULT_TIMEOUT


class HttpClientApplication(Application):
    async def on_bind(self, event: FactoryBindEvent):
        # todo timeout config ?
        # todo lazy build ?
        transport = AsyncHTTPTransport()
        cache_transport = AsyncCacheTransport(transport=transport)
        event.container.add_instance(
            AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                transport=cache_transport,
            )
        )

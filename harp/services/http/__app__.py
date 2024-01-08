from hishel import AsyncCacheTransport
from httpx import AsyncClient, AsyncHTTPTransport

from harp.config import Application
from harp.config.factories.events import FactoryBindEvent


class HttpApplication(Application):
    async def on_bind(self, event: FactoryBindEvent):
        # todo timeout config ?
        # todo lazy build ?
        transport = AsyncHTTPTransport()
        cache_transport = AsyncCacheTransport(transport=transport)
        event.container.add_instance(
            AsyncClient(
                timeout=10.0,
                transport=cache_transport,
            )
        )

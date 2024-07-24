from httpx import AsyncClient

from harp.config.events import FactoryBoundEvent
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import ProxySettings


class ProxyLifecycle:
    @staticmethod
    async def on_bound(event: FactoryBoundEvent):
        settings = event.provider.get(ProxySettings)
        for endpoint in settings.endpoints:
            event.resolver.add(
                endpoint.port,
                HttpProxyController(
                    endpoint.url,
                    name=endpoint.name,
                    dispatcher=event.dispatcher,
                    http_client=event.provider.get(AsyncClient),
                ),
            )

"""
Proxy Application

"""
from httpx import AsyncClient

from harp.apps.proxy.controllers import HttpProxyController
from harp.apps.proxy.settings import ProxySettings
from harp.config.application import Application
from harp.config.events import FactoryBoundEvent


class ProxyApplication(Application):
    depends_on = ["harp.services.http"]

    settings_namespace = "proxy"
    settings_type = ProxySettings
    settings: ProxySettings

    @classmethod
    def defaults(cls, settings=None) -> dict:
        settings = settings or super().defaults()
        settings.setdefault("endpoints", [])
        return settings

    async def on_bound(self, event: FactoryBoundEvent):
        for endpoint in self.settings.endpoints:
            event.resolver.add(
                endpoint.port,
                HttpProxyController(
                    endpoint.url,
                    name=endpoint.name,
                    dispatcher=event.dispatcher,
                    http_client=event.provider.get(AsyncClient),
                ),
            )

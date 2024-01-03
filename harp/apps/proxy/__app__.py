"""
Proxy Application

"""
from harp.apps.proxy.controllers import HttpProxyController
from harp.apps.proxy.settings import ProxySettings
from harp.config.application import Application
from harp.config.factories.events import FactoryBoundEvent


class ProxyApplication(Application):
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
                endpoint.port, HttpProxyController(endpoint.url, name=endpoint.name, dispatcher=event.dispatcher)
            )

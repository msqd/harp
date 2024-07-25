"""
Proxy Application

"""

from httpx import AsyncClient

from harp.config import Application
from harp.config.events import OnBoundEvent

from .controllers import HttpProxyController
from .settings import ProxySettings


async def on_bound(event: OnBoundEvent):
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


application = Application(
    on_bound=on_bound,
    settings_type=ProxySettings,
)

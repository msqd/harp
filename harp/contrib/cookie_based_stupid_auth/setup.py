from config.common import Configuration
from rodi import Container
from whistle.protocols import IAsyncEventDispatcher

from harp import get_logger
from harp.core.asgi.events import EVENT_CORE_REQUEST
from harp.core.asgi.events.request import RequestEvent
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.factories.events import EVENT_FACTORY_BIND
from harp.factories.events.bind import ProxyFactoryBindEvent

logger = get_logger(__name__)

DEFAULT_STUPID_TOKEN = "lydian dominant"


async def authentication_failed_controller(request: ASGIRequest, response: ASGIResponse):
    await response.start(status=401, headers={"content-type": "text/plain"})
    await response.body(b"Authentication failed.")


class CookieBasedStupidAuthFirewall:
    def __init__(self, token: str):
        self.token = token

    async def on_core_request_check_auth(self, event: RequestEvent):
        if event.request.cookies.get("harp") != self.token:
            event.set_controller(authentication_failed_controller)


def register(container: Container, dispatcher: IAsyncEventDispatcher, settings: Configuration):
    logger.info("Registering cookie based stupid auth ...")
    settings._data.setdefault("stupid_token", DEFAULT_STUPID_TOKEN)
    dispatcher.listeners.add(EVENT_FACTORY_BIND, on_bind)


async def on_bind(event: ProxyFactoryBindEvent):
    firewall = CookieBasedStupidAuthFirewall(event.settings.stupid_token)
    event.dispatcher.listeners.add(EVENT_CORE_REQUEST, firewall.on_core_request_check_auth)

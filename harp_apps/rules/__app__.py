from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_REQUEST, EVENT_FILTER_RESPONSE, ProxyFilterEvent

from .settings import RulesSettings

logger = get_logger(__name__)


class RulesApplication(Application):
    settings_namespace = "rules"
    settings_type = RulesSettings

    async def on_bind(self, event: FactoryBindEvent):
        logger.warning("Rules application is currently an experimental early prototype. THE API MAY CHANGE A LOT.")

    async def on_bound(self, event: FactoryBoundEvent):
        dispatcher = event.provider.get(IAsyncEventDispatcher)
        dispatcher.add_listener(EVENT_FILTER_REQUEST, self.on_filter_request)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, self.on_filter_remote_request)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, self.on_filter_remote_response)
        dispatcher.add_listener(EVENT_FILTER_RESPONSE, self.on_filter_response)

    async def on_filter_request(self, event: ProxyFilterEvent):
        key = event.name, str(event.request), "on_request"
        context = {"endpoint": key[0], "request": event.request, "logger": logger}
        for rule in self.settings.rules.match(*key):
            exec(rule, None, context)

    async def on_filter_remote_request(self, event: HttpClientFilterEvent):
        endpoint = event.request.extensions.get("harp", {}).get("endpoint")
        if not endpoint:
            return
        fingerprint = f"{event.request.method} {event.request.url.raw_path.decode()}"
        context = {"endpoint": endpoint, "request": event.request, "logger": logger}
        for rule in self.settings.rules.match(endpoint, fingerprint, "on_remote_request"):
            exec(rule, None, context)

    async def on_filter_remote_response(self, event: HttpClientFilterEvent):
        endpoint = event.request.extensions.get("harp", {}).get("endpoint")
        if not endpoint:
            return
        fingerprint = f"{event.request.method} {event.request.url.raw_path.decode()}"
        context = {"endpoint": endpoint, "response": event.response, "logger": logger}
        for rule in self.settings.rules.match(endpoint, fingerprint, "on_remote_response"):
            exec(rule, None, context)

    async def on_filter_response(self, event: ProxyFilterEvent):
        key = event.name, str(event.request), "on_response"
        context = {"endpoint": key[0], "response": event.response, "logger": logger}
        for rule in self.settings.rules.match(*key):
            exec(rule, None, context)

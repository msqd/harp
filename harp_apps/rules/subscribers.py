from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_REQUEST, EVENT_FILTER_RESPONSE, ProxyFilterEvent

from .models.rulesets import RuleSet
from .models.scripts import Script

logger = get_logger(__name__)


class RulesSubscriber:
    def __init__(self, rules: RuleSet):
        self.rules = rules

    def subscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.add_listener(EVENT_FILTER_REQUEST, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_RESPONSE, self.on_filter_event)

    def unsubscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.remove_listener(EVENT_FILTER_REQUEST, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_RESPONSE, self.on_filter_event)

    def match(self, *args):
        return self.rules.match(*args)

    def execute(self, script: Script, globals, locals):
        try:
            return script.execute(locals, globals=globals)
        except Exception as e:
            logger.exception(e)

    async def on_filter_event(self, event: ProxyFilterEvent | HttpClientFilterEvent):
        for script in self.match(*event.criteria):
            self.execute(script, event.globals, event.locals)

from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_FILTER_PROXY_RESPONSE, ProxyFilterEvent

from .models.rulesets import RuleSet

logger = get_logger(__name__)


class RulesSubscriber:
    def __init__(self, ruleset: RuleSet):
        self.ruleset = ruleset
        self._warned = set()

    def subscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.add_listener(EVENT_FILTER_PROXY_REQUEST, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, self.on_filter_event)
        dispatcher.add_listener(EVENT_FILTER_PROXY_RESPONSE, self.on_filter_event)

    def unsubscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.remove_listener(EVENT_FILTER_PROXY_REQUEST, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, self.on_filter_event)
        dispatcher.remove_listener(EVENT_FILTER_PROXY_RESPONSE, self.on_filter_event)

    def match(self, *args):
        return self.ruleset.match(*args)

    def _warn_query_dependent(self, event: HttpClientFilterEvent, scripts: list):
        """Remote levels still match the path with its query string; a rule only matching that way will not match
        once they move to the path-only form every other level uses."""
        endpoint, _, rule = event.criteria
        path_only = list(self.match(endpoint, event.path_fingerprint, rule))
        for script in scripts:
            if script in path_only or id(script) in self._warned:
                continue
            self._warned.add(id(script))
            logger.warning(
                f"Deprecated: a {rule} rule matched {event.fingerprint!r} thanks to its query string. Remote levels "
                f"will match the path only ({event.path_fingerprint!r}) in the next release, rewrite the pattern."
            )

    async def on_filter_event(self, event: ProxyFilterEvent | HttpClientFilterEvent):
        scripts = list(self.match(*event.criteria))
        if isinstance(event, HttpClientFilterEvent):
            self._warn_query_dependent(event, scripts)
        for script in scripts:
            try:
                event.execute_script(script)
            except Exception as e:
                logger.error(f"Error executing script {script}: {e}", exc_info=True)

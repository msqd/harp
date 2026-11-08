import asyncio
from concurrent.futures import ThreadPoolExecutor

from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.http import HttpResponse
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_FILTER_PROXY_RESPONSE, ProxyFilterEvent

from .metrics import RULES_FAILURES
from .models.rulesets import RuleSet

logger = get_logger(__name__)

#: Seconds a rule may run before it is given up on.
DEFAULT_TIME_BUDGET = 1.0

#: Threads running rules. A rule that outlives its budget keeps its thread, so they are bounded and kept apart from
#: the loop's default executor.
MAX_RULE_THREADS = 8

#: The only level whose failure stops the transaction, the others let it go on unfiltered.
FAIL_CLOSED_RULE = "on_request"


class RulesSubscriber:
    def __init__(self, ruleset: RuleSet, /, *, time_budget: float = DEFAULT_TIME_BUDGET):
        if time_budget <= 0:
            raise ValueError(f"The time budget must be positive, got {time_budget!r}.")
        self.ruleset = ruleset
        self.time_budget = time_budget
        self._warned = set()
        self._executor = ThreadPoolExecutor(max_workers=MAX_RULE_THREADS, thread_name_prefix="harp-rules")

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
        self._executor.shutdown(wait=False)

    def match(self, *args, **options):
        return self.ruleset.match(*args, **options)

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

    def _scripts_for(self, event: ProxyFilterEvent | HttpClientFilterEvent) -> list:
        """The scripts matching the event, plus those matching its alternate fingerprints (each script once)."""
        endpoint, _, rule = event.criteria
        # Only the normalised path of the proxy levels gets the trailing slash retry, not the raw remote paths.
        options = {"trailing_slash": not isinstance(event, HttpClientFilterEvent)}
        scripts = list(self.match(*event.criteria, **options))
        for fingerprint in getattr(event, "alternate_fingerprints", ()):
            scripts += [s for s in self.match(endpoint, fingerprint, rule, **options) if s not in scripts]
        return scripts

    async def on_filter_event(self, event: ProxyFilterEvent | HttpClientFilterEvent):
        scripts = self._scripts_for(event)
        if isinstance(event, HttpClientFilterEvent):
            self._warn_query_dependent(event, scripts)
        for script in scripts:
            if not await self._run(event, script):
                break

    async def _run(self, event: ProxyFilterEvent | HttpClientFilterEvent, script) -> bool:
        """Run one script in a worker thread, without blocking the loop. Returns whether the next ones may run."""
        context = event.create_execution_context()
        try:
            await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(self._executor, script, context), self.time_budget
            )
            event.apply_script_context(context)
        except TimeoutError:
            # The thread cannot be stopped, it is left to finish and its context is dropped.
            return self._fail(event, script, "timeout", f"exceeded its time budget of {self.time_budget}s")
        except Exception as exc:  # noqa: BLE001
            return self._fail(event, script, "error", f"{type(exc).__name__}: {exc}", exc_info=True)
        return True

    def _fail(self, event, script, reason: str, detail: str, **log_kwargs) -> bool:
        rule = event._get_rule_name()
        RULES_FAILURES.labels(endpoint=event.endpoint, rule=rule, reason=reason).inc()
        message = (
            f"Rule {rule} {getattr(script, 'filename', script)!r} on endpoint {event.endpoint!r} failed ({detail})"
        )
        if rule == FAIL_CLOSED_RULE:
            logger.error(f"{message}, the request is answered with an error.", **log_kwargs)
            event.set_response(HttpResponse("Internal Server Error", status=500, content_type="text/plain"))
            return False
        logger.warning(f"{message}, carrying on without it.", **log_kwargs)
        return True

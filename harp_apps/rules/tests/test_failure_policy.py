import asyncio
import time

import httpx
import pytest
from prometheus_client import REGISTRY
from whistle import AsyncEventDispatcher

from harp.http import HttpRequest, HttpResponse
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_FILTER_PROXY_RESPONSE, ProxyFilterEvent

from ..models.rulesets import RuleSet
from ..subscribers import RulesSubscriber


def _subscriber(rules: dict, **kwargs):
    ruleset = RuleSet()
    ruleset.add({"api": {"*": rules}})
    dispatcher = AsyncEventDispatcher()
    RulesSubscriber(ruleset, **kwargs).subscribe(dispatcher)
    return dispatcher


def _failures(rule: str, reason: str):
    labels = {"endpoint": "api", "rule": rule, "reason": reason}
    return REGISTRY.get_sample_value("rules_failures_count_total", labels) or 0


async def test_failing_on_request_rule_fails_closed():
    dispatcher = _subscriber({"on_request": ["raise ValueError('boom')", "response = None"]})
    event = ProxyFilterEvent("api", request=HttpRequest())

    await dispatcher.adispatch(EVENT_FILTER_PROXY_REQUEST, event)

    assert event.response.status == 500
    assert b"boom" not in event.response.body


async def test_failing_on_request_rule_stops_the_remaining_rules():
    dispatcher = _subscriber(
        {
            "on_request": [
                "raise ValueError('boom')",
                "from harp.http import HttpResponse\nresponse = HttpResponse('late')",
            ]
        }
    )
    event = ProxyFilterEvent("api", request=HttpRequest())

    await dispatcher.adispatch(EVENT_FILTER_PROXY_REQUEST, event)

    assert event.response.status == 500


async def test_failing_on_response_rule_fails_open_with_a_warning_naming_the_rule(caplog):
    dispatcher = _subscriber({"on_response": "raise ValueError('boom')"})
    original = HttpResponse("ok", status=200)
    event = ProxyFilterEvent("api", request=HttpRequest(), response=original)
    before = _failures("on_response", "error")

    with caplog.at_level("WARNING"):
        await dispatcher.adispatch(EVENT_FILTER_PROXY_RESPONSE, event)

    assert event.response is original
    messages = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("on_response" in m and "<rule:" in m and "boom" in m for m in messages)
    assert _failures("on_response", "error") == before + 1


async def test_failing_remote_request_rule_fails_open():
    dispatcher = _subscriber({"on_remote_request": "raise ValueError('boom')"})
    request = httpx.Request("GET", "http://example.com/", extensions={"harp": {"endpoint": "api"}})
    event = HttpClientFilterEvent(request)

    await dispatcher.adispatch(EVENT_FILTER_HTTP_CLIENT_REQUEST, event)

    assert event.response is None


async def test_rule_reading_the_streamed_body_fails_open_naming_the_rule(caplog):
    dispatcher = _subscriber({"on_response": "size = len(response.body)"})
    streamed = HttpResponse(b"", status=200)
    streamed.stream = iter(())
    event = ProxyFilterEvent("api", request=HttpRequest(), response=streamed)

    with caplog.at_level("WARNING"):
        await dispatcher.adispatch(EVENT_FILTER_PROXY_RESPONSE, event)

    assert event.response is streamed
    assert any("on_response" in r.getMessage() and "aread" in r.getMessage() for r in caplog.records)


async def test_rule_over_the_time_budget_fails_closed_on_request(caplog):
    dispatcher = _subscriber({"on_request": "import time\ntime.sleep(0.5)"}, time_budget=0.05)
    event = ProxyFilterEvent("api", request=HttpRequest())
    before = _failures("on_request", "timeout")

    started = time.perf_counter()
    with caplog.at_level("WARNING"):
        await dispatcher.adispatch(EVENT_FILTER_PROXY_REQUEST, event)

    assert time.perf_counter() - started < 0.4
    assert event.response.status == 500
    assert any("time budget" in r.getMessage() and "on_request" in r.getMessage() for r in caplog.records)
    assert _failures("on_request", "timeout") == before + 1


async def test_rule_over_the_time_budget_is_ignored_on_other_levels():
    dispatcher = _subscriber({"on_response": "import time\ntime.sleep(0.5)\nresponse = None"}, time_budget=0.05)
    original = HttpResponse("ok", status=200)
    event = ProxyFilterEvent("api", request=HttpRequest(), response=original)

    await dispatcher.adispatch(EVENT_FILTER_PROXY_RESPONSE, event)
    await asyncio.sleep(0.6)

    assert event.response is original


async def test_slow_rule_does_not_block_other_requests():
    dispatcher = _subscriber({"on_request": "import time\ntime.sleep(0.3)"}, time_budget=1)
    slow = ProxyFilterEvent("api", request=HttpRequest())

    ticks = []

    async def ticker():
        for _ in range(5):
            await asyncio.sleep(0.02)
            ticks.append(time.perf_counter())

    started = time.perf_counter()
    await asyncio.gather(dispatcher.adispatch(EVENT_FILTER_PROXY_REQUEST, slow), ticker())

    assert ticks[0] - started < 0.15
    assert slow.response is None


@pytest.mark.parametrize("budget", [0, -1])
def test_time_budget_must_be_positive(budget):
    with pytest.raises(ValueError):
        RulesSubscriber(RuleSet(), time_budget=budget)

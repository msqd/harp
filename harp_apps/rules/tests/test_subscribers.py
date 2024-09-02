from typing import cast
from unittest.mock import Mock

import httpx
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.http import HttpRequest, HttpResponse
from harp_apps.http_client.events import (
    EVENT_FILTER_HTTP_CLIENT_REQUEST,
    EVENT_FILTER_HTTP_CLIENT_RESPONSE,
    HttpClientFilterEvent,
)
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, ProxyFilterEvent

from ..models.rulesets import RuleSet
from ..subscribers import RulesSubscriber


async def _dispatch_filter_event(dispatcher, event_name, event):
    event.set_response = Mock()
    await dispatcher.adispatch(event_name, event)
    return event.set_response


async def _dispatch_proxy_filter_event(dispatcher, endpoint, event_name) -> Mock:
    return await _dispatch_filter_event(
        dispatcher,
        event_name,
        ProxyFilterEvent(endpoint, request=HttpRequest()),
    )


async def _dispatch_http_client_filter_event(dispatcher, endpoint, event_name) -> Mock:
    return await _dispatch_filter_event(
        dispatcher,
        event_name,
        HttpClientFilterEvent(
            httpx.Request(
                "GET",
                "http://example.com/",
                extensions={"harp": {"endpoint": endpoint}},
            ),
        ),
    )


async def test_rules_subscriber_set_response():
    class Handler:
        def __init__(self):
            self.responses = [
                HttpResponse("Hello.", status=200),
                httpx.Response(200, text="Hello."),
                httpx.Response(200, text="Goodbye."),
                HttpResponse("Goodbye.", status=200),
            ]

        def __call__(self, context):
            context["response"] = self.responses.pop(0)

    mock = Mock()

    # rules
    ruleset = RuleSet()
    ruleset.add({"filtered": {"*": {"*": Handler()}}, "unfiltered": {"*": {"*": mock}}})
    subscriber = RulesSubscriber(ruleset)

    # dispatcher
    dispatcher = cast(IAsyncEventDispatcher, AsyncEventDispatcher())
    subscriber.subscribe(dispatcher)

    # on_request
    callback = await _dispatch_proxy_filter_event(dispatcher, "unfiltered", EVENT_FILTER_PROXY_REQUEST)
    assert not callback.called
    callback = await _dispatch_proxy_filter_event(dispatcher, "filtered", EVENT_FILTER_PROXY_REQUEST)
    assert callback.called
    assert isinstance(callback.call_args[0][0], HttpResponse)

    # on_remote_request
    callback = await _dispatch_http_client_filter_event(dispatcher, "unfiltered", EVENT_FILTER_HTTP_CLIENT_REQUEST)
    assert not callback.called
    callback = await _dispatch_http_client_filter_event(dispatcher, "filtered", EVENT_FILTER_HTTP_CLIENT_REQUEST)
    assert callback.called
    assert isinstance(callback.call_args[0][0], httpx.Response)

    # on_remote_response
    callback = await _dispatch_http_client_filter_event(dispatcher, "unfiltered", EVENT_FILTER_HTTP_CLIENT_RESPONSE)
    assert not callback.called
    callback = await _dispatch_http_client_filter_event(dispatcher, "filtered", EVENT_FILTER_HTTP_CLIENT_RESPONSE)
    assert callback.called
    assert isinstance(callback.call_args[0][0], httpx.Response)

    # on_response
    callback = await _dispatch_proxy_filter_event(dispatcher, "unfiltered", EVENT_FILTER_PROXY_REQUEST)
    assert not callback.called
    callback = await _dispatch_proxy_filter_event(dispatcher, "filtered", EVENT_FILTER_PROXY_REQUEST)
    assert callback.called
    assert isinstance(callback.call_args[0][0], HttpResponse)

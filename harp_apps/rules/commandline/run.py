import asyncio
from typing import cast

import click
from whistle import IAsyncEventDispatcher

from harp.commandline.options.server import add_harp_config_options
from harp.config import ConfigurationBuilder
from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.http import HttpRequest
from harp.utils.urls import normalize_url
from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, EVENT_FILTER_HTTP_CLIENT_RESPONSE
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_FILTER_PROXY_RESPONSE
from harp_apps.proxy.settings import Remote

from .utils.dump import (
    on_proxy_request_dump,
    on_proxy_response_dump,
    on_remote_request_dump,
    on_remote_response_dump,
    on_remote_response_show_cache_control,
)
from .utils.loaders import load_ruleset_from_files
from .utils.subscribers import DebugRulesSubscriber


@click.command("run")
@add_harp_config_options
@click.argument("endpoint")
@click.argument("method")
@click.argument("path")
def run_command(files, examples, options, endpoint, method, path):
    try:
        endpoint_name, endpoint_target = endpoint.split("=", 1)
    except ValueError:
        raise click.BadParameter("Endpoint must be in the format name=url")
    endpoint_target = normalize_url(endpoint_target)

    ruleset = load_ruleset_from_files(files, examples, options)

    dispatcher: IAsyncEventDispatcher = cast(IAsyncEventDispatcher, LoggingAsyncEventDispatcher())

    system = asyncio.run(
        ConfigurationBuilder({"applications": ["http_client", "rules"]}, use_default_applications=False).abuild_system()
    )

    http_client = system.provider.get("http_client")

    dispatcher.add_listener(EVENT_FILTER_PROXY_REQUEST, on_proxy_request_dump, priority=-100)
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, on_remote_request_dump, priority=-100)
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, on_remote_response_dump, priority=-100)
    dispatcher.add_listener(
        EVENT_FILTER_HTTP_CLIENT_RESPONSE,
        on_remote_response_show_cache_control,
        priority=-100,
    )
    dispatcher.add_listener(
        EVENT_FILTER_HTTP_CLIENT_RESPONSE,
        on_remote_response_show_cache_control,
        priority=100,
    )
    dispatcher.add_listener(EVENT_FILTER_PROXY_RESPONSE, on_proxy_response_dump, priority=-100)

    # Create a proxy controller to mimic the real behavious of the proxy.
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": endpoint_target}]}),
        name=endpoint_name,
        dispatcher=dispatcher,
        http_client=http_client,
    )

    rules_subscriber = DebugRulesSubscriber(ruleset)
    rules_subscriber.subscribe(dispatcher)

    request = HttpRequest(method=method, path=path)
    asyncio.run(controller(request))

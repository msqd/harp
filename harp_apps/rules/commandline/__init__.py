import asyncio
from typing import cast

from click import BaseCommand
from httpx import AsyncClient, AsyncHTTPTransport
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.tree import Tree
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.commandline.options.server import add_harp_config_options
from harp.config.examples import get_example_filename
from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.http import HttpRequest
from harp.http.tests.stubs import HttpRequestStubBridge
from harp.utils.commandline import click
from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, EVENT_FILTER_HTTP_CLIENT_RESPONSE
from harp_apps.http_client.transport import AsyncFilterableTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_FILTER_REQUEST, EVENT_FILTER_RESPONSE
from harp_apps.rules.commandline.utils.dump import (
    on_proxy_request_dump,
    on_proxy_response_dump,
    on_remote_request_dump,
    on_remote_response_dump,
)
from harp_apps.rules.models.rulesets import RuleSet
from harp_apps.rules.subscribers import RulesSubscriber

logger = get_logger(__name__)


@click.group("rules")
def entrypoint():
    """Rules engine related commands."""
    pass


console = Console(force_terminal=True)


def load_ruleset(filenames: list[str]) -> RuleSet:
    raise NotImplementedError("This function is not used anymore.")
    rules = {}
    for filename in filenames:
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            from harp.utils.config import yaml

            rules |= yaml.load(filename).get("rules", {})
        elif filename.endswith(".toml"):
            from harp.utils.config import toml

            rules |= toml.load(filename).get("rules", {})
        else:
            raise click.UsageError(f"Unsupported file format: {filename}")

    return RuleSet(rules)


def load_ruleset_from_files(files, examples, options):
    from harp_apps.rules.settings import RulesSettings

    # todo not easy to implement for now, and not really important for this command
    if len(options):
        raise click.UsageError("Unsupported options: " + ", ".join(options))

    settings = RulesSettings()
    for file in files:
        settings.load(file)
    for example in examples:
        settings.load(get_example_filename(example))
    ruleset = settings.rules
    return ruleset


def iter_ruleset(ruleset):
    for endpoint_pattern, endpoint_rules in ruleset.rules.items():
        for request_pattern, request_rules in endpoint_rules.items():
            for event_pattern, scripts in request_rules.items():
                yield endpoint_pattern, request_pattern, event_pattern, scripts


@entrypoint.command("lint")
@add_harp_config_options
def lint(files, examples, options):
    """Lint the rules."""

    ruleset = load_ruleset_from_files(files, examples, options)

    rules_tree = Tree(":shuffle_tracks_button: Rules")
    for endpoint_pattern, endpoint_rules in ruleset.rules.items():
        endpoint_tree = rules_tree.add(
            Syntax("endpoint LIKE " + repr(endpoint_pattern.source), "sql", background_color="default")
        )
        for request_pattern, request_rules in endpoint_rules.items():
            request_tree = endpoint_tree.add(
                Syntax("request LIKE " + repr(request_pattern.source), "sql", background_color="default")
            )
            for event_pattern, scripts in request_rules.items():
                event_tree = request_tree.add(
                    Syntax("event LIKE " + repr(event_pattern.source), "sql", background_color="default")
                )
                event_tree.add(
                    Syntax(
                        "\n".join((f"# {script.filename.strip('<>')}\n" + script.source for script in scripts)).strip(),
                        "python",
                        background_color="default",
                    )
                )
    console.print(rules_tree)


lint = cast(BaseCommand, lint)


class DebugRulesSubscriber(RulesSubscriber):
    def match(self, *args):
        scripts = list(super().match(*args))

        elements = []
        for i, script in enumerate(scripts):
            elements.append(
                Syntax(
                    "# " + script.filename.strip("<>") + "\n" + script.source.strip(),
                    "python",
                    background_color="default",
                )
            )
            if i:
                elements.append(Rule())

        if len(elements):
            console.print(
                Padding(
                    Panel(
                        Group(*elements),
                        title=f":shuffle_tracks_button: [bright_white]Rule – {args[2]}[/bright_white] ([bright_green]{len(scripts)}[/bright_green] script(s) found)",
                        expand=True,
                        title_align="left",
                    ),
                    (0, 0, 0, 8) if args[2].startswith("on_remote_") else (0, 0, 0, 4),
                )
            )

        yield from scripts


@entrypoint.command("test")
@add_harp_config_options
@click.argument("endpoint")
@click.argument("method")
@click.argument("path")
def test(files, examples, options, endpoint, method, path):
    ruleset = load_ruleset_from_files(files, examples, options)

    dispatcher: IAsyncEventDispatcher = cast(IAsyncEventDispatcher, LoggingAsyncEventDispatcher(logger=logger))
    http_client = AsyncClient(
        transport=AsyncFilterableTransport(
            transport=AsyncHTTPTransport(),
            dispatcher=dispatcher,
        )
    )
    dispatcher.add_listener(EVENT_FILTER_REQUEST, on_proxy_request_dump, priority=-100)
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_REQUEST, on_remote_request_dump, priority=-100)
    dispatcher.add_listener(EVENT_FILTER_HTTP_CLIENT_RESPONSE, on_remote_response_dump, priority=100)
    dispatcher.add_listener(EVENT_FILTER_RESPONSE, on_proxy_response_dump, priority=100)
    controller = HttpProxyController(
        "https://httpbin.org/",
        name=endpoint,
        dispatcher=dispatcher,
        http_client=http_client,
    )

    rules_subscriber = DebugRulesSubscriber(ruleset)
    rules_subscriber.subscribe(dispatcher)

    request = HttpRequest(HttpRequestStubBridge(method=method, path=path))
    asyncio.run(controller(request))

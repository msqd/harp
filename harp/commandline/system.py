import asyncio
import orjson
from rich.console import Console
from rich.pretty import Pretty
from rich.syntax import Syntax
from rich.tree import Tree

from harp.commandline.options.server import CommonServerOptions, _server_click_options
from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.commandline import click


def _format_value(value):
    """Format a value for display, handling LazyServiceReference and ServiceProvider specially."""
    from rodi import InstanceProvider
    from harp.services.providers import ServiceProvider
    from harp.services.references import LazyServiceReference

    if isinstance(value, LazyServiceReference):
        return f"!ref {value.target}"
    if isinstance(value, ServiceProvider):
        # Show it as a dependency reference
        type_name = value._type.__name__ if hasattr(value._type, "__name__") else str(value._type)
        return f"→ {type_name}"
    if isinstance(value, InstanceProvider):
        # Show the type of the instance
        if hasattr(value, "instance"):
            instance_type = type(value.instance).__name__
            return f"→ {instance_type}"
        return "→ (instance)"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = ", ".join(f"{k}: {_format_value(v)}" for k, v in value.items())
        return f"{{{items}}}"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        items = ", ".join(_format_value(v) for v in value)
        return f"[{items}]"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def _choose_primary_key(keys):
    """Choose the best primary key from a list of keys, preferring human-friendly names."""
    string_keys = [k for k in keys if isinstance(k, str)]

    if not string_keys:
        return None

    # Prioritize by:
    # 1. Names with dots (namespace-like): http_client.proxy_transport, storage.engine
    # 2. Names with underscores: http_client, storage_settings
    # 3. Lowercase names over PascalCase
    # 4. Shorter names

    def key_priority(key):
        has_dot = "." in key
        has_underscore = "_" in key
        is_pascal_case = key[0].isupper() if key else False
        length = len(key)

        # Return tuple for sorting (lower is better)
        # Prioritize: has_dot (0 is best), has_underscore, is_pascal_case, length
        return (not has_dot, not has_underscore, is_pascal_case, length)

    return min(string_keys, key=key_priority)


def _print_services(console: Console, system_obj):
    """Print all configured services in a tree structure."""
    from collections import defaultdict
    from harp.services.providers import ServiceProvider

    # Get all services from the provider's _map
    services_map = system_obj.provider._map

    if not services_map:
        console.print("[yellow]No services configured.[/yellow]")
        return

    # Build a reverse map: provider ID -> list of all keys (for finding aliases)
    provider_to_keys = defaultdict(list)
    for key, provider in services_map.items():
        if isinstance(provider, ServiceProvider):
            provider_to_keys[id(provider)].append(key)

    # Create a main tree for services
    tree = Tree("🔧 [bright_white][bold]Configured Services[/bright_white][/bold]")

    # Collect unique services (one per provider) with their best primary key
    unique_services = []
    seen_provider_ids = set()

    for provider_id, all_keys in provider_to_keys.items():
        if provider_id in seen_provider_ids:
            continue

        # Choose the best primary key for this provider
        primary_key = _choose_primary_key(all_keys)
        if not primary_key:
            continue

        # Get the provider from the map
        provider = services_map[primary_key]

        unique_services.append((primary_key, provider, all_keys))
        seen_provider_ids.add(provider_id)

    # Sort services by name for better readability
    sorted_services = sorted(unique_services, key=lambda x: x[0])

    for service_name, provider, all_keys in sorted_services:
        # Get service type
        service_type = provider._type
        type_str = f"{service_type.__module__}.{service_type.__name__}"

        # Get lifestyle
        lifestyle = provider._lifestyle.name if hasattr(provider._lifestyle, "name") else str(provider._lifestyle)

        # Get aliases (all other keys that point to this provider, excluding the primary key)
        aliases = [k for k in all_keys if isinstance(k, str) and k != service_name]

        # Create service entry
        service_tree = tree.add(f"[cyan]{service_name}[/cyan]")
        service_tree.add(f"Type: [green]{type_str}[/green]")
        service_tree.add(f"Lifestyle: [yellow]{lifestyle}[/yellow]")

        # Show aliases if any
        if aliases:
            aliases_str = ", ".join(f"[dim]{alias}[/dim]" for alias in sorted(aliases))
            service_tree.add(f"Aliases: {aliases_str}")

        # Show constructor if custom
        if provider._constructor:
            service_tree.add(f"Constructor: [dim]{provider._constructor}[/dim]")

        # Show keyword arguments (dependencies and configuration)
        if provider._kwargs:
            kwargs_tree = service_tree.add("[magenta]Arguments[/magenta]")
            for key, value in provider._kwargs.items():
                kwargs_tree.add(f"{key}: {_format_value(value)}")

        # Show positional arguments if any
        if provider._args:
            args_tree = service_tree.add("[magenta]Positionals[/magenta]")
            for i, value in enumerate(provider._args):
                args_tree.add(f"[{i}]: {_format_value(value)}")

    console.print(tree)
    console.print(f"\n[dim]Total services: {len(unique_services)}[/dim]")


@click.group("system", short_help="System inspection commands.")
def system():
    """Inspect system configuration and services.

    These commands allow you to view the compiled configuration and registered services,
    which is useful for debugging and understanding how your HARP instance is set up.
    """
    pass


@system.command("config", short_help="Prints the current configuration.")
@click.option("--raw", is_flag=True, help="Prints the raw configuration as a dictionary.")
@click.option("--json", is_flag=True, help="Prints the raw configuration as JSON.")
@click.option(
    "--unsecure",
    is_flag=True,
    help="Prints the configuration without hiding sensitive information.",
)
@_server_click_options
def config_subcommand(raw=False, json=False, unsecure=False, **kwargs):
    """Compiles and dumps the current configuration.

    Example:

        $ harp-proxy system config --file ... --example ... --set ...

    """
    if raw and json:
        raise click.UsageError("Cannot use both --raw and --json.")

    system_obj = asyncio.run(
        ConfigurationBuilder.from_commandline_options(
            CommonServerOptions(**kwargs),
        ).abuild_system()
    )

    console = Console()

    if raw:
        console.print(Pretty(asdict(system_obj.config)))
    elif json:
        console.print(
            Syntax(
                orjson.dumps(
                    asdict(
                        system_obj.config,
                        secure=not unsecure,
                    ),
                    option=orjson.OPT_INDENT_2,
                ).decode(),
                "json",
                background_color="default",
            )
        )
    else:
        for k, v in system_obj.config.items():
            tree = Tree(f"📦 [bright_white][bold]{k}[/bright_white][/bold]")
            # todo secure/unsecure with pretty print ?
            tree.add(Pretty(v))
            console.print(tree)


@system.command("services", short_help="Prints the configured services.")
@_server_click_options
def services_subcommand(**kwargs):
    """Prints all configured services with their dependencies and configuration.

    Example:

        $ harp-proxy system services --file config.yml

    """
    system_obj = asyncio.run(
        ConfigurationBuilder.from_commandline_options(
            CommonServerOptions(**kwargs),
        ).abuild_system()
    )

    console = Console()
    _print_services(console, system_obj)

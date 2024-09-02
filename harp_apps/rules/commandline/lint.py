from rich.syntax import Syntax
from rich.tree import Tree

from harp.commandline.options.server import add_harp_config_options
from harp.utils.commandline import click
from harp.utils.console import console

from .utils.loaders import load_ruleset_from_files


@click.command("lint")
@add_harp_config_options
def lint_command(files, examples, options):
    """Lint the rules."""

    ruleset = load_ruleset_from_files(files, examples, options)

    rules_tree = Tree(":shuffle_tracks_button: Rules")
    for endpoint_pattern, endpoint_rules in ruleset.rules.items():
        endpoint_tree = rules_tree.add(
            Syntax(
                "endpoint LIKE " + repr(endpoint_pattern.source),
                "sql",
                background_color="default",
            )
        )
        for request_pattern, request_rules in endpoint_rules.items():
            request_tree = endpoint_tree.add(
                Syntax(
                    "request LIKE " + repr(request_pattern.source),
                    "sql",
                    background_color="default",
                )
            )
            for event_pattern, scripts in request_rules.items():
                event_tree = request_tree.add(
                    Syntax(
                        "event LIKE " + repr(event_pattern.source),
                        "sql",
                        background_color="default",
                    )
                )
                event_tree.add(
                    Syntax(
                        "\n".join((f"# {script.filename.strip('<>')}\n" + script.source for script in scripts)).strip(),
                        "python",
                        background_color="default",
                    )
                )
    console.print(rules_tree)

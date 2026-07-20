import json
import os
import shutil
import subprocess
import tempfile
from typing import cast

from click import BaseCommand

from harp.commandline import cookiecutters as templates
from harp.utils.commandline import click

DEFAULT_AUTHOR_NAME = "Smart Anonymous Harpist"
DEFAULT_AUTHOR_EMAIL = "anonymous@harp-proxy.net"


def get_git_config(key):
    """Return a git config value (e.g. ``user.name``), or None if unset or git is unavailable."""
    try:
        result = subprocess.run(["git", "config", key], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _cookiecutter_command():
    """Resolve how to run cookiecutter: the installed binary, or `uv tool run` as a fallback."""
    if shutil.which("cookiecutter"):
        return ["cookiecutter"]
    if shutil.which("uv"):
        return ["uv", "tool", "run", "cookiecutter"]
    raise click.UsageError(
        "Install cookiecutter with `uv add harp-proxy --extra dev`, or ensure `uv` is available to "
        "run it via `uv tool run`."
    )


@click.command("create", short_help="Creates a templated directory using cookiecutter (project...).")
@click.argument("template", type=click.Choice(["project"], case_sensitive=False))
@click.argument("name", required=False)
@click.option("--no-app", is_flag=True, help="Do not create an application folder for custom code.")
@click.option("--no-config", is_flag=True, help="Do not create a config.yml file.")
def create(template, name, no_app, no_config):
    """Creates a new project using cookiecutter.

    The project name can be passed as an argument to skip the interactive prompt; author
    information is taken from your git config when available. Use --no-app / --no-config to
    opt out of the application folder or the config file.
    """

    command = _cookiecutter_command()
    template_path = os.path.join(templates.__path__[0], template)

    if not name:
        name = click.prompt("Project name")
    author_name = get_git_config("user.name") or click.prompt("Author name", default=DEFAULT_AUTHOR_NAME)
    author_email = get_git_config("user.email") or click.prompt("Author email", default=DEFAULT_AUTHOR_EMAIL)

    context = {
        "name": name,
        "author_name": author_name,
        "author_email": author_email,
        "create_application": not no_app,
        "create_config": not no_config,
    }

    # cookiecutter runs as a subprocess (possibly in its own environment via `uv tool run`), so we
    # cannot pass a Python context directly. A JSON config file is valid YAML, which lets cookiecutter
    # read real booleans -- CLI `key=value` overrides would arrive as strings and break the template's
    # boolean conditionals.
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_file = os.path.join(tmp_dir, "cookiecutter_config.json")
        with open(config_file, "w") as fp:
            json.dump({"default_context": context}, fp)

        subprocess.run([*command, "--no-input", "--config-file", config_file, template_path], check=True)


create = cast(BaseCommand, create)

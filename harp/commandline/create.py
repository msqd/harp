import importlib.metadata
import json
import os
import shutil
import subprocess
import tempfile
from typing import cast

from click import BaseCommand
from packaging.version import Version

from harp.commandline import cookiecutters as templates
from harp.config.example import render_example_config
from harp.utils.commandline import click

DEFAULT_AUTHOR_NAME = "Smart Anonymous Harpist"
DEFAULT_AUTHOR_EMAIL = "anonymous@harp-proxy.net"

#: Cookiecutter version run through ``uv tool run`` when it is not installed, pinned for reproducibility.
COOKIECUTTER_SPEC = "cookiecutter==2.6.0"


def literal(value: str) -> str:
    """Wrap a value so cookiecutter, which renders context values as Jinja, keeps it verbatim."""
    return "{% raw %}" + value.replace("{% endraw %}", "{% endraw %}{{ '{% endraw %}' }}{% raw %}") + "{% endraw %}"


def get_git_config(key):
    """Return a git config value (e.g. ``user.name``), or None if unset or git is unavailable."""
    try:
        result = subprocess.run(["git", "config", key], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def harp_requirement(version: str) -> str:
    """Return the ``harp-proxy`` requirement a project scaffolded by this harp should depend on.

    PEP 440 excludes pre-releases from ``>=X.Y.Z``, so a pre-release or dev build floors at
    ``X.Y.Z.dev0``, the lowest version of that release.
    """
    parsed = Version(version)
    release = ".".join(str(part) for part in parsed.release)
    return f"harp-proxy>={release}.dev0" if parsed.is_prerelease else f"harp-proxy>={release}"


def _cookiecutter_command():
    """Resolve how to run cookiecutter: the installed binary, or `uv tool run` as a fallback."""
    if shutil.which("cookiecutter"):
        return ["cookiecutter"]
    if shutil.which("uv"):
        return ["uv", "tool", "run", "--from", COOKIECUTTER_SPEC, "cookiecutter"]
    raise click.UsageError(
        "Install cookiecutter with `pip install cookiecutter`, or ensure `uv` is available to run it via `uv tool run`."
    )


@click.command("create", short_help="Creates a templated directory using cookiecutter (project...).")
@click.argument("template", type=click.Choice(["project"], case_sensitive=False))
@click.argument("name", required=False)
@click.option("--no-app", is_flag=True, help="Do not create an application folder for custom code.")
@click.option("--no-config", is_flag=True, help="Do not create a config.yml file.")
@click.option(
    "--harp-source",
    envvar="HARP_SOURCE",
    type=click.Path(file_okay=False, resolve_path=True),
    help="Path to a local harp checkout to install editable instead of the released harp-proxy (env: HARP_SOURCE).",
)
def create(template, name, no_app, no_config, harp_source):
    """Creates a new project using cookiecutter.

    The project name can be passed as an argument to skip the interactive prompt; author
    information is taken from your git config when available. Use --no-app / --no-config to
    opt out of the application folder or the config file. The project depends on ``harp-proxy``
    at least at the installed version (``.dev0`` floor for pre-releases and dev builds), unless --harp-source points to a local harp
    checkout, which is installed editable instead (handy to test unreleased changes).
    """

    command = _cookiecutter_command()
    if harp_source and not os.path.isfile(os.path.join(harp_source, "pyproject.toml")):
        raise click.UsageError(f"--harp-source {harp_source!r} is not a harp checkout (no pyproject.toml found).")
    template_path = os.path.join(templates.__path__[0], template)

    if not name:
        name = click.prompt("Project name")
    author_name = get_git_config("user.name") or click.prompt("Author name", default=DEFAULT_AUTHOR_NAME)
    author_email = get_git_config("user.email") or click.prompt("Author email", default=DEFAULT_AUTHOR_EMAIL)

    context = {
        "name": literal(name),
        "author_name": literal(author_name),
        "author_email": literal(author_email),
        "create_application": not no_app,
        "create_config": not no_config,
        "__harp_source": literal(harp_source or ""),
        "__harp_requirement": harp_requirement(importlib.metadata.version("harp-proxy")),
        # A commented, source-introspected reference config.yml; empty when config is skipped.
        "__example_config": "" if no_config else render_example_config(),
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

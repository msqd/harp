import os
import shutil
import subprocess
from typing import cast

from click import BaseCommand

from harp.commandline import cookiecutters as templates
from harp.utils.commandline import click


@click.command("create", short_help="Creates a templated directory using cookiecutter (project...).")
@click.argument("template", type=click.Choice(["project"], case_sensitive=False))
def create(template):
    """Creates a new project using cookiecutter."""

    template_path = os.path.join(templates.__path__[0], template)

    if shutil.which("cookiecutter"):
        subprocess.run(["cookiecutter", template_path], check=True)
    elif shutil.which("uv"):
        subprocess.run(["uv", "tool", "run", "cookiecutter", template_path], check=True)
    else:
        raise click.UsageError(
            "Install cookiecutter with `uv add harp-proxy --extra dev`, or ensure `uv` is available to "
            "run it via `uv tool run`."
        )


create = cast(BaseCommand, create)

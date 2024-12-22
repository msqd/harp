import os

from harp.commandline import cookiecutters as templates
from harp.utils.commandline import check_packages, click


@click.command("create", short_help="Creates a templated directory using cookiecutter (project...).")
@click.argument("template", type=click.Choice(["project"], case_sensitive=False))
def create(template):
    """Creates a new project using cookiecutter."""

    if not check_packages("cookiecutter"):
        raise click.UsageError(
            "You need to install cookiecutter to use this command (or use the `dev` extra, for example using "
            "`pip install harp-proxy[dev]` or `poetry install -E dev`)."
        )

    from cookiecutter.main import cookiecutter

    cookiecutter(os.path.join(templates.__path__[0], template))

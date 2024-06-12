import asyncio
from concurrent.futures import ThreadPoolExecutor

from click.testing import CliRunner

from harp.commandline import migrations


async def run_cli_migrate_command(database_url, /, *, operation="up", revision="head"):
    """
    Run the `migrate` command from the CLI, synchronously, in a thread (via ThreadPoolExecutor). This uses click's
    CliRunner which is a testing helper. You should not use this outside tests, as it will setup a fully separate harp
    instance with its own configuration, etc.

    :param database_url:
    :param operation: up or down
    :param revision: target revision ("head" for latest, "base" for initial or specific revision number)
    :return:
    """

    def _migrate():
        cli = CliRunner()
        return cli.invoke(migrations.migrate, [operation, revision, "--set", "storage.url=" + database_url])

    with ThreadPoolExecutor() as executor:
        result = await asyncio.get_event_loop().run_in_executor(executor, _migrate)

    return result

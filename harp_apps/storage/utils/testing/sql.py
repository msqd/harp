import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Union

from click.testing import CliRunner
from pydantic_core import MultiHostUrl, Url
from sqlalchemy import URL, make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from harp.commandline import migrations


async def run_cli_migrate_command(url: Union[str | URL | Url | MultiHostUrl], /, *, operation="up", revision="head"):
    """
    Run the `migrate` command from the CLI, synchronously, in a thread (via ThreadPoolExecutor). This uses click's
    CliRunner which is a testing helper. You should not use this outside tests, as it will setup a fully separate harp
    instance with its own configuration, etc.

    :param url:
    :param operation: up or down
    :param revision: target revision ("head" for latest, "base" for initial or specific revision number)
    :return:
    """
    if isinstance(url, (Url, MultiHostUrl)):
        url = str(url)

    url = make_url(url)

    def _migrate():
        cli = CliRunner()
        return cli.invoke(
            migrations.migrate,
            [
                operation,
                revision,
                "--set",
                "storage.url=" + url.render_as_string(hide_password=False),
            ],
        )

    with ThreadPoolExecutor() as executor:
        result = await asyncio.get_event_loop().run_in_executor(executor, _migrate)

    return result


@asynccontextmanager
async def get_scoped_database_url(database_url, test_id):
    """
    Returns a "scoped" database URL that is unique to the test_id, with a database available to run some tests. Logic
    differs a bit depending on the target dialect, but the idea is to create a new database for each test, and drop it
    afterward. For sqlite, we bypass this as the "migration" process is a simple reset+recreate all.

    :param database_url:
    :param test_id:
    :return:
    """
    admin_url = make_url(database_url)
    dialect = admin_url.get_dialect().name

    if dialect == "mysql":
        admin_url = admin_url.set(username="root")

    admin_engine = create_async_engine(admin_url.render_as_string(hide_password=False))

    if dialect == "sqlite":
        try:
            yield database_url
        finally:
            await admin_engine.dispose()

    elif dialect in ("mysql", "postgresql"):
        db_name = f"test_{test_id}"
        url = make_url(database_url).set(database=db_name)

        async with admin_engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")

            await conn.execute(text(f"CREATE DATABASE {url.database}"))
            if dialect == "mysql":
                await conn.execute(text(f"GRANT ALL PRIVILEGES ON {url.database}.* TO '{url.username}'@'%'"))

        try:
            yield url.render_as_string(hide_password=False)
        finally:
            async with admin_engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                await conn.execute(text(f"DROP DATABASE {url.database}"))
            await admin_engine.dispose()

    else:
        raise RuntimeError(f"Unsupported dialect «{admin_engine.dialect.name}»")


def create_database_container_for(dialect, image, driver):
    """
    Create a database container for the given dialect, image and driver.
    This is a generator that yields the connection url (DSN) for the database container, once it is ready to accept
    connections.

    It's primarily used to write pytest fixtures that connects to this containairized database.

    :param dialect:
    :param image:
    :param driver:

    :return: str
    """
    if dialect == "sqlite":
        yield f"{dialect}+{driver}:///:memory:"
    elif dialect == "postgresql":
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer(image) as container:
            yield container.get_connection_url().replace("postgresql+psycopg2://", f"{dialect}+{driver}://")
    elif dialect == "mysql":
        from testcontainers.mysql import MySqlContainer

        with MySqlContainer(image) as container:
            yield container.get_connection_url().replace("mysql+pymysql://", f"{dialect}+{driver}://")
    elif dialect == "mssql":
        from testcontainers.mssql import SqlServerContainer

        with SqlServerContainer() as container:
            yield container.get_connection_url().replace("mssql+pymssql://", f"{dialect}+{driver}://")
    else:
        raise ValueError(f"Unsupported or invalid dialect: {dialect!r}")

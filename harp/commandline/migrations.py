import asyncio
import importlib
from functools import partial
from typing import cast

from alembic import command
from click import Command
from pyheck import upper_camel
from sqlalchemy.ext.asyncio import create_async_engine

from harp import get_logger
from harp.commandline.options.server import server_command
from harp.utils.commandline import click
from harp_apps.storage.utils.migrations import (
    create_alembic_config,
    create_harp_settings_with_storage_from_command_line_options,
    create_revision,
    current_revisions_by_application,
    do_migrate,
    do_reset,
)

logger = get_logger(__name__)


async def print_status(engine, alembic_cfg):
    """Print the revision each application's branch is at."""
    if engine.dialect.name == "sqlite":
        click.echo("sqlite schemas are not tracked by alembic.")
        return
    try:
        async with engine.connect() as conn:
            current = await conn.run_sync(lambda sync_conn: current_revisions_by_application(sync_conn, alembic_cfg))
    finally:
        await engine.dispose()
    for application, revision in sorted(current.items()):
        click.echo(f"{application}: {revision or 'not migrated'}")


@server_command("db:migrate")
@click.argument("operation", nargs=1, type=click.Choice(["up", "down", "status"]))
@click.argument("revision", nargs=1, required=False)
@click.option("--reset", is_flag=True, help="Reset the database (drop all before migrations).")
def migrate(*, operation, revision, reset=False, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    if operation == "status":
        asyncio.run(print_status(engine, alembic_cfg))
        return
    if not revision:
        raise click.UsageError(f"{operation!r} needs a revision ('heads' for the latest of every application).")

    if operation == "up":
        migrator = partial(command.upgrade, alembic_cfg, revision)
    elif operation == "down":
        migrator = partial(command.downgrade, alembic_cfg, revision)
    else:
        raise ValueError(f"Invalid operation {operation}.")

    asyncio.run(do_migrate(engine, migrator=migrator, reset=reset))


migrate = cast(Command, migrate)


@server_command("db:create-migration")
@click.argument("application", nargs=1)
@click.argument("message", nargs=1)
def create_migration(*, application, message, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    try:
        create_revision(alembic_cfg, application, message)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from None


create_migration = cast(Command, create_migration)


@server_command("db:merge")
@click.argument("message", nargs=1)
@click.argument("revisions", nargs=-1)
def run_db_merge_command(*, message, revisions, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    command.merge(alembic_cfg, message=message or "merge migration", revisions=revisions)


run_db_merge_command = cast(Command, run_db_merge_command)


@server_command("db:feature")
@click.argument("operation", nargs=1, type=click.Choice(["add", "remove"]))
@click.argument("features", nargs=-1)
def feature(features, operation, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)

    implementations = {}
    for feature in features:
        _module = importlib.import_module(f"harp_apps.storage.optionals.{feature}")
        implementations[feature] = getattr(_module, upper_camel(feature + "_optional"))(
            alembic_cfg.get_main_option("sqlalchemy.url")
        )

    for feature in features:
        if operation == "add":
            asyncio.run(implementations[feature].install())
        elif operation == "remove":
            asyncio.run(implementations[feature].uninstall())
        else:
            raise ValueError(f"Invalid operation {operation}.")


feature = cast(Command, feature)


@server_command("db:history")
def history(**kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    command.history(alembic_cfg)


history = cast(Command, history)


@server_command("db:reset")
def reset(**kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    asyncio.run(do_reset(engine))


reset = cast(Command, reset)

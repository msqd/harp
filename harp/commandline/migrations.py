import asyncio
import importlib
from functools import partial
from typing import cast

from alembic import command
from click import BaseCommand
from pyheck import upper_camel
from sqlalchemy.ext.asyncio import create_async_engine

from harp import get_logger
from harp.commandline.options.server import server_command
from harp.utils.commandline import click
from harp_apps.storage.utils.migrations import (
    create_alembic_config,
    create_harp_settings_with_storage_from_command_line_options,
    do_migrate,
    do_reset,
)

logger = get_logger(__name__)


@server_command("db:migrate")
@click.argument("operation", nargs=1, type=click.Choice(["up", "down"]))
@click.argument("revision", nargs=1)
@click.option("--reset", is_flag=True, help="Reset the database (drop all before migrations).")
def migrate(*, operation, revision, reset=False, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    if operation == "up":
        migrator = partial(command.upgrade, alembic_cfg, revision)
    elif operation == "down":
        migrator = partial(command.downgrade, alembic_cfg, revision)
    else:
        raise ValueError(f"Invalid operation {operation}.")

    asyncio.run(do_migrate(engine, migrator=migrator, reset=reset))


migrate = cast(BaseCommand, migrate)


@server_command("db:create-migration")
@click.argument("message", nargs=1)
def create_migration(*, message, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    command.revision(alembic_cfg, autogenerate=True, message=message or "auto-generated migration")


create_migration = cast(BaseCommand, create_migration)


@server_command("db:merge")
@click.argument("message", nargs=1)
@click.argument("revisions", nargs=-1)
def run_db_merge_command(*, message, revisions, **kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    command.merge(alembic_cfg, message=message or "merge migration", revisions=revisions)


run_db_merge_command = cast(BaseCommand, run_db_merge_command)


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


feature = cast(BaseCommand, feature)


@server_command("db:history")
def history(**kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    command.history(alembic_cfg)


history = cast(BaseCommand, history)


@server_command("db:reset")
def reset(**kwargs):
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    alembic_cfg = create_alembic_config(settings.get("storage").url)
    engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    asyncio.run(do_reset(engine))


reset = cast(BaseCommand, reset)

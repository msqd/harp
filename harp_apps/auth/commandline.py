"""Commands of the authentication application."""

import asyncio
from typing import Optional, cast

from click import Command
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from harp.commandline.options.server import server_command
from harp.errors import OutdatedSchemaError
from harp.security.actor import Role
from harp.utils.commandline import click
from harp_apps.auth.models import AccountKind, AccountsRepository
from harp_apps.storage.utils.migrations import (
    create_harp_settings_with_storage_from_command_line_options,
    ensure_schema_is_current,
    render_failure,
)


class AccountExistsError(Exception):
    pass


async def _create_account(url, values: dict) -> None:
    engine = create_async_engine(str(url))
    try:
        await ensure_schema_is_current(engine)
        accounts = AccountsRepository(async_sessionmaker(engine, expire_on_commit=False))
        try:
            await accounts.create(values)
        except IntegrityError as exc:
            raise AccountExistsError(render_failure(exc, url)) from None
    finally:
        await engine.dispose()


@server_command("auth:create-account")
@click.argument("username")
@click.option(
    "--role",
    required=True,
    type=click.Choice([role.label for role in Role]),
    help="What the account may do: viewer reads, editor also acts on traffic, admin also manages access.",
)
@click.option("--display-name", help="Name shown in the dashboard.")
@click.option("--email", help="Email of the account, shown and never a way in.")
def create_account(*, username: str, role: str, display_name: Optional[str], email: Optional[str], **kwargs):
    """Creates an account, which is also how access is recovered when no Admin is left."""
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    values = {
        "username": username,
        "kind": AccountKind.PERSON,
        "role": Role.parse(role),
        "display_name": display_name,
        "email": email,
    }
    try:
        asyncio.run(_create_account(settings.get("storage").url, values))
    except OutdatedSchemaError as exc:
        raise click.ClickException(str(exc)) from None
    except AccountExistsError:
        # the username and the email are both unique
        raise click.ClickException(_what_exists(username, email)) from None
    click.echo(f"Account {username} created, as {role}.")


def _what_exists(username: str, email: Optional[str]) -> str:
    if email is None:
        return f"An account named {username} already exists."
    return f"An account named {username} or with the email {email} already exists."


create_account = cast(Command, create_account)

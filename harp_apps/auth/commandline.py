"""Commands of the authentication application."""

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Optional, cast

from click import Command
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from harp.commandline.options.server import server_command
from harp.errors import OutdatedSchemaError
from harp.security.actor import Role
from harp.utils.commandline import click
from harp_apps.auth.models import (
    PASSWORD_METHOD,
    Account,
    AccountKind,
    AccountsRepository,
    Identity,
    UsernameRefused,
    check_username,
)
from harp_apps.auth.passwords import PasswordHasher, PasswordPolicyError, check_policy
from harp_apps.storage.utils.migrations import (
    create_harp_settings_with_storage_from_command_line_options,
    ensure_schema_is_current,
    render_failure,
)


class AccountExistsError(Exception):
    pass


async def _create_account(url, values: dict, password: str) -> None:
    """Creates the account and its password identity together: both exist or none does."""
    engine = create_async_engine(str(url))
    try:
        await ensure_schema_is_current(engine)
        password_hash = await PasswordHasher().hash(password)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                account = Account(**values)
                session.add(account)
                await session.flush()
                session.add(
                    Identity(
                        account_id=account.id,
                        method=PASSWORD_METHOD,
                        issuer="",
                        subject=account.username,
                        password_hash=password_hash,
                    )
                )
                await session.commit()
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
@click.option(
    "--generate-password",
    is_flag=True,
    help="Make up the password and show it once, instead of asking for one.",
)
def create_account(
    *,
    username: str,
    role: str,
    display_name: Optional[str],
    email: Optional[str],
    generate_password: bool,
    **kwargs,
):
    """Creates an account with a password, which is also how access is recovered when no Admin is left."""
    try:
        check_username(username)
    except UsernameRefused as exc:
        raise click.ClickException(str(exc)) from None
    password = _generate_password() if generate_password else _ask_password()
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    values = {
        "username": username,
        "kind": AccountKind.PERSON,
        "role": Role.parse(role),
        "display_name": display_name,
        "email": email,
    }
    try:
        asyncio.run(_create_account(settings.get("storage").url, values, password))
    except OutdatedSchemaError as exc:
        raise click.ClickException(str(exc)) from None
    except AccountExistsError:
        # the username and the email are both unique
        raise click.ClickException(_what_exists(username, email)) from None
    click.echo(f"Account {username} created, as {role}.")
    if generate_password:
        click.echo(f"Password: {password}")
        click.echo("It is shown this once and stored hashed: keep it somewhere safe.")


def _generate_password() -> str:
    # 24 characters of 6 bits each: well past the policy, and nothing a person has to read out loud
    return secrets.token_urlsafe(18)


def _ask_password() -> str:
    """Asks for the password until the policy accepts it (the input is not shown)."""
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    try:
        check_policy(password)
    except PasswordPolicyError as exc:
        raise click.ClickException(str(exc)) from None
    return password


def _what_exists(username: str, email: Optional[str]) -> str:
    if email is None:
        return f"An account named {username} already exists."
    return f"An account named {username} or with the email {email} already exists."


create_account = cast(Command, create_account)


async def _update_account(url, username: str, **values) -> None:
    engine = create_async_engine(str(url))
    try:
        await ensure_schema_is_current(engine)
        await AccountsRepository(async_sessionmaker(engine, expire_on_commit=False)).update_account(username, **values)
    finally:
        await engine.dispose()


def _update(kwargs, username: str, **values) -> None:
    settings = create_harp_settings_with_storage_from_command_line_options(kwargs)
    try:
        asyncio.run(_update_account(settings.get("storage").url, username, **values))
    except OutdatedSchemaError as exc:
        raise click.ClickException(str(exc)) from None
    except NoResultFound:
        raise click.ClickException(
            f"There is no account named {username} (system accounts cannot be changed)."
        ) from None


@server_command("auth:set-role")
@click.argument("username")
@click.argument("role", type=click.Choice([role.label for role in Role]))
def set_role(*, username: str, role: str, **kwargs):
    """Sets the role of an account. Takes effect at its next request."""
    _update(kwargs, username, role=Role.parse(role))
    click.echo(f"Account {username} is now {role}.")


@server_command("auth:disable-account")
@click.argument("username")
def disable_account(*, username: str, **kwargs):
    """Revokes an account without deleting it: it answers 401 at its next request. Undo with auth:enable-account."""
    _update(kwargs, username, disabled_at=datetime.now(UTC))
    click.echo(f"Account {username} is disabled.")


@server_command("auth:enable-account")
@click.argument("username")
def enable_account(*, username: str, **kwargs):
    """Enables an account that was disabled."""
    _update(kwargs, username, disabled_at=None)
    click.echo(f"Account {username} is enabled.")


set_role = cast(Command, set_role)
disable_account = cast(Command, disable_account)
enable_account = cast(Command, enable_account)

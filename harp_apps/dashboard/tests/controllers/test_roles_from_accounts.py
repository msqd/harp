"""The dashboard with the real resolver: the role of a request is the one of its account, read from the database."""

from base64 import b64encode
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import orjson
import pytest
from http_router import Router
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.http import HttpRequest
from harp.security.actor import Role
from harp_apps.auth.actors import ActorResolver
from harp_apps.auth.models import Account, AccountsRepository
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.storage.conftest import *  # noqa: F401,F403
from harp_apps.storage.types import IStorage

USERS = ("alice", "carol", "dave", "erin")


@pytest.fixture
async def accounts(sql_engine):
    accounts = AccountsRepository(async_sessionmaker(sql_engine, expire_on_commit=False))
    await accounts.create({"username": "alice", "role": Role.EDITOR, "display_name": "Alice"})
    await accounts.create({"username": "carol", "role": Role.VIEWER})
    await accounts.create({"username": "dave", "role": Role.ADMIN})
    return accounts


@pytest.fixture
async def dashboard(accounts):
    router = Router(trim_last_slash=True)
    SystemController(storage=MagicMock(spec=IStorage), settings={}, resolver=MagicMock(), router=router)
    controller = DashboardController(
        storage=Mock(spec=IStorage),
        settings=DashboardSettings(
            auth=BasicAuthSettings(type="basic", algorithm="plaintext", users={u: User(password="x") for u in USERS}),
            devserver={"enabled": True, "port": 5173},
        ),
        http_client=Mock(spec=AsyncClient),
        router=router,
        actors=ActorResolver(accounts),
    )
    controller._ui_devserver_proxy_controller = None
    return controller


async def change(accounts, username, **values):
    async with accounts.session_factory() as session:
        await session.execute(update(Account).where(Account.username == username).values(**values))
        await session.commit()


async def call(dashboard, username, path="/api/system/"):
    headers = {"authorization": "basic " + b64encode(f"{username}:x".encode()).decode()}
    return await dashboard(HttpRequest(path=path, headers=headers), AsyncMock())


async def test_the_system_page_tells_the_role_of_the_account(dashboard):
    response = await call(dashboard, "alice")

    assert response.status == 200
    body = orjson.loads(response.body)
    assert (body["user"], body["displayName"], body["role"]) == ("alice", "Alice", "editor")


async def test_a_viewer_account_is_refused_what_needs_an_editor(dashboard):
    assert (await call(dashboard, "carol", "/api/system/proxy")).status == 403


async def test_an_editor_account_is_refused_what_needs_an_admin(dashboard):
    assert (await call(dashboard, "alice", "/api/system/settings")).status == 403


async def test_a_demotion_applies_at_the_next_request(dashboard, accounts):
    assert (await call(dashboard, "dave", "/api/system/settings")).status == 200

    await change(accounts, "dave", role=Role.VIEWER)

    assert (await call(dashboard, "dave", "/api/system/settings")).status == 403


async def test_a_disabled_account_answers_401_even_with_the_right_password(dashboard, accounts):
    await change(accounts, "carol", disabled_at=datetime.now(UTC))

    response = await call(dashboard, "carol")

    assert response.status == 401
    assert response.headers["www-authenticate"].startswith("Basic")


async def test_a_user_of_the_configuration_without_account_yet_is_an_admin(dashboard, accounts):
    response = await call(dashboard, "erin", "/api/system/settings")

    assert response.status == 200
    assert (await accounts.find_one({"username": "erin"})).role is Role.ADMIN

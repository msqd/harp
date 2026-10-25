"""
The dashboard requires a login by default: without a configured ``dashboard.auth``, a random password is generated at
each boot and logged once. ``dashboard.auth.type: none`` is the explicit opt-out.
"""

import asyncio
import logging
import re
from base64 import b64encode

import orjson
import pytest
from sqlalchemy import select

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.passwords import hash_password
from harp_apps.dashboard.settings import DashboardSettings
from harp_apps.storage.models import User as SqlUser

DASHBOARD_PORT = 4080

#: Paths that are not registered on the router but are served (or forwarded) by the dashboard port.
EXTRA_PATHS = ("/", "/index.html", "/assets/app.js", "/no/such/page", "/no-such-file.txt", "/metrics", "/api/unknown")

PASSWORD_LOG = re.compile(r"username=(?P<username>\S+) password=(?P<password>\S+)")


def basic(username, password):
    return [(b"authorization", b"Basic " + b64encode(f"{username}:{password}".encode()))]


@pytest.fixture(autouse=True)
def static_assets(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>dashboard</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('dashboard')")
    monkeypatch.setattr(DashboardController, "static_build_path", str(tmp_path))


@pytest.fixture
async def boot(test_api, caplog):
    systems = []

    async def _boot(dashboard=None, *, storage_url="sqlite:///:memory:"):
        builder = ConfigurationBuilder(use_default_applications=False)
        for app in ("http_client", "proxy", "storage", "dashboard"):
            builder.applications.add(app)
        builder.add_values(
            {
                "storage": {"url": storage_url, "migrate": True},
                "dashboard": {"devserver": {"enabled": False}, **(dashboard or {})},
                "proxy": {"endpoints": [{"port": 80, "name": "test", "url": test_api.url}]},
            }
        )
        with caplog.at_level(logging.INFO):
            system = await builder.abuild_system(validate_dependencies=False)
        systems.append(system)
        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()
        return system, client

    yield _boot

    for system in systems:
        await system.dispose()


def logged_credentials(caplog):
    return [m.groupdict() for m in PASSWORD_LOG.finditer(caplog.text)]


def dashboard_routes(system):
    """Every (method, path) registered on the dashboard router, parameters filled in."""
    routes = []
    for route in system.provider.get("dashboard.router").routes():
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        routes.extend((method, path) for method in sorted(route.methods))
    return routes


async def get(client, method, path, headers=None):
    return await client.http_request(method, path, headers=headers, port=DASHBOARD_PORT)


def header(response, name):
    return {k.lower(): v for k, v in response["headers"]}.get(name)


class TestDefaultDashboardAuth:
    async def test_generated_credentials_are_logged_once(self, boot, caplog):
        await boot()

        (credentials,) = logged_credentials(caplog)
        assert credentials["username"] == "admin"
        assert len(credentials["password"]) >= 22  # 128 bits, url-safe base64

    async def test_credentials_are_new_at_every_boot(self, boot, caplog):
        await boot()
        await boot()

        first, second = logged_credentials(caplog)
        assert first["password"] != second["password"]

    async def test_every_route_requires_the_logged_credentials(self, boot, caplog):
        system, client = await boot()
        (credentials,) = logged_credentials(caplog)
        good = basic(credentials["username"], credentials["password"])
        bad = basic(credentials["username"], "wrong")

        targets = dashboard_routes(system) + [("GET", path) for path in EXTRA_PATHS]
        assert ("PUT", "/api/system/proxy") in targets  # the table really walks the router

        failures = []
        for method, path in targets:
            for headers in (None, bad):
                response = await get(client, method, path, headers)
                if response["status"] != 401 or not header(response, b"www-authenticate"):
                    failures.append((method, path, "anonymous" if headers is None else "wrong", response["status"]))
            if (await get(client, method, path, good))["status"] == 401:
                failures.append((method, path, "logged credentials", 401))

        assert failures == []

    @pytest.mark.parametrize("path", ["/", "/index.html", "/assets/app.js", "/metrics", "/api/system/settings"])
    async def test_logged_credentials_open_the_dashboard(self, boot, caplog, path):
        _, client = await boot()
        (credentials,) = logged_credentials(caplog)

        response = await get(client, "GET", path, basic(credentials["username"], credentials["password"]))

        assert response["status"] == 200

    async def test_unauthenticated_proxy_update_changes_nothing(self, boot, caplog, test_api):
        _, client = await boot()
        (credentials,) = logged_credentials(caplog)
        good = basic(credentials["username"], credentials["password"])

        async def endpoint_status():
            response = await get(client, "GET", "/api/system/proxy", good)
            assert response["status"] == 200
            return orjson.loads(response["body"])["endpoints"][0]["remote"]["endpoints"][0]["status"]

        before = await endpoint_status()
        body = b'{"endpoint": "test", "action": "down", "index": 0}'
        response = await client.http_request("PUT", "/api/system/proxy", body=body, port=DASHBOARD_PORT)

        assert response["status"] == 401
        assert await endpoint_status() == before
        assert (await client.http_get("/echo", port=80))["status"] == 200

    async def test_password_is_nowhere_but_the_boot_log(self, boot, caplog):
        system, client = await boot()
        (credentials,) = logged_credentials(caplog)
        good = basic(credentials["username"], credentials["password"])

        for path in ("/api/system/settings", "/api/system/storage"):
            body = (await get(client, "GET", path, good))["body"].decode()
            assert credentials["password"] not in body
        assert credentials["password"] not in repr(asdict(system.config, secure=False, verbose=True))
        assert caplog.text.count(credentials["password"]) == 1

    async def test_generated_auth_is_not_copied_into_the_settings(self, boot, caplog):
        system, client = await boot()
        (credentials,) = logged_credentials(caplog)
        good = basic(credentials["username"], credentials["password"])

        assert system.provider.get(DashboardSettings).auth is None
        response = await get(client, "GET", "/api/system/settings", good)
        assert orjson.loads(response["body"])["dashboard"].get("auth") is None

    async def test_repeated_boots_leave_one_user_row(self, boot, tmp_path):
        url = f"sqlite:///{tmp_path}/harp.db"

        async def admin_rows(storage):
            async with storage.session_factory() as session:
                return (await session.execute(select(SqlUser.username).where(SqlUser.username == "admin"))).all()

        for _ in range(2):
            system, _client = await boot(storage_url=url)
            storage = system.provider.get("storage")
            await system.provider.get("dashboard.controller")._create_users_task
            for _attempt in range(60):  # the user is created by the storage worker, once the database is ready
                if await admin_rows(storage):
                    break
                await asyncio.sleep(0.05)

        assert await admin_rows(storage) == [("admin",)]


class TestDashboardAuthOptOut:
    async def test_none_leaves_the_dashboard_open(self, boot):
        _, client = await boot({"auth": {"type": "none"}})

        assert (await get(client, "GET", "/"))["status"] == 200
        assert (await get(client, "GET", "/api/system/settings"))["status"] == 200

    async def test_none_warns_at_every_boot(self, boot, caplog):
        await boot({"auth": {"type": "none"}})

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "unauthenticated" in r.getMessage()]
        assert len(warnings) == 1
        assert "proxied traffic" in warnings[0].getMessage()
        assert logged_credentials(caplog) == []


class TestExplicitBasicAuth:
    BASIC = {
        "auth": {
            "type": "basic",
            "algorithm": "pbkdf2_sha256",
            "users": {"alice": {"password": hash_password("pbkdf2_sha256", "s3cret")}},
        }
    }

    async def test_configured_users_work_and_nothing_is_generated(self, boot, caplog):
        _, client = await boot(self.BASIC)

        assert (await get(client, "GET", "/"))["status"] == 401
        assert (await get(client, "GET", "/", basic("alice", "s3cret")))["status"] == 200
        assert (await get(client, "GET", "/", basic("admin", "s3cret")))["status"] == 401
        assert logged_credentials(caplog) == []
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING and "ashboard" in r.getMessage()]


class TestMetricsPort:
    async def test_metrics_port_serves_only_metrics(self, boot):
        system, _ = await boot({"auth": {"type": "none"}, "metrics_port": 9100})
        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        assert (await client.http_get("/metrics", port=9100))["status"] == 200
        for path in ("/", "/api/system/settings", "/api/transactions/", "/anything"):
            assert (await client.http_get(path, port=9100))["status"] == 404

    async def test_metrics_port_stays_open_under_default_auth(self, boot):
        system, _ = await boot({"metrics_port": 9100})
        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        assert (await client.http_get("/metrics", port=9100))["status"] == 200


class TestWebsocket:
    async def test_dashboard_port_accepts_no_websocket_upgrade(self, boot):
        """No websocket is served today. Should one be added, it must go through the dashboard authentication."""
        from unittest.mock import AsyncMock

        system, _ = await boot()
        send = AsyncMock()

        await system.asgi_app(
            {"type": "websocket", "path": "/", "server": ("localhost", DASHBOARD_PORT)}, AsyncMock(), send
        )

        send.assert_not_called()

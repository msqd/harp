"""
The dashboard requires a sign-in, and there is no way around it. With nothing configured, the password method is on with
no account: the setup link HARP logs at start lets the first administrator in, and every other route answers 401 (or
sends a browser to the sign-in page) until somebody is signed in.
"""

import asyncio
import logging
import re
from base64 import b64encode

import orjson
import pytest

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.dashboard.controllers import DashboardController

DASHBOARD_PORT = 4080

#: Paths that are not registered on the router but are served (or forwarded) by the dashboard port.
EXTRA_PATHS = ("/", "/index.html", "/assets/app.js", "/no/such/page", "/no-such-file.txt", "/metrics", "/api/unknown")

#: What anybody may reach, since it is how one signs in.
PUBLIC = {
    ("GET", "/signin"),
    ("GET", "/setup"),
    ("GET", "/auth.js"),
    ("POST", "/api/auth/signin"),
    ("POST", "/api/auth/setup"),
}

SETUP_LINK = re.compile(r"/setup#(?P<secret>[A-Za-z0-9_-]{43})")
PASSWORD = "correct horse battery staple"
JSON = [
    (b"content-type", b"application/json"),
    (b"host", b"harp.test"),
    (b"origin", b"http://harp.test"),
]


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
            builder.applications.add(app, autoload_dependencies=True)
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


def setup_links(caplog):
    return [m.group("secret") for m in SETUP_LINK.finditer(caplog.text)]


def dashboard_routes(system):
    """Every (method, path) registered on the dashboard router, parameters filled in."""
    routes = []
    for route in system.provider.get("dashboard.router").routes():
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        routes.extend((method, path) for method in sorted(route.methods))
    return routes


async def get(client, method, path, headers=None, body=None):
    return await client.http_request(method, path, headers=headers, body=body or b"", port=DASHBOARD_PORT)


def header(response, name):
    return {k.lower(): v for k, v in response["headers"]}.get(name)


async def set_up(client, caplog) -> list:
    """Accepts the setup link of the logs, returns the headers that carry the session of the new Admin."""
    (secret,) = setup_links(caplog)[-1:]
    body = orjson.dumps({"secret": secret, "username": "root", "password": PASSWORD})
    response = await get(client, "POST", "/api/auth/setup", JSON, body)
    assert response["status"] == 200, response["body"]
    cookie = header(response, b"set-cookie").decode().split(";", 1)[0]
    return [(b"cookie", cookie.encode())]


class TestDefaultDashboardAuth:
    async def test_the_setup_link_is_logged_once_and_replaced_at_every_boot(self, boot, caplog):
        await boot()
        await boot()

        first, second = setup_links(caplog)
        assert first != second

    async def test_nobody_gets_in_before_the_link_is_accepted(self, boot, caplog):
        system, client = await boot()

        targets = dashboard_routes(system) + [("GET", path) for path in EXTRA_PATHS]
        assert ("PUT", "/api/system/proxy") in targets  # the table really walks the router

        failures = []
        for method, path in targets:
            if (method, path) in PUBLIC:
                continue
            response = await get(client, method, path, JSON if method != "GET" else None)
            # a browser fetching a page is sent to sign in, anything else is refused
            if response["status"] not in (401, 302) or (response["status"] == 302 and method != "GET"):
                failures.append((method, path, response["status"]))
            if response["status"] == 302 and header(response, b"location") != b"/signin":
                failures.append((method, path, header(response, b"location")))

        assert failures == []

    async def test_signing_in_before_the_link_is_accepted_is_refused(self, boot):
        _, client = await boot()

        body = orjson.dumps({"username": "root", "password": PASSWORD})
        response = await get(client, "POST", "/api/auth/signin", JSON, body)

        assert response["status"] == 401

    async def test_the_pages_are_public(self, boot):
        _, client = await boot()

        for path in ("/signin", "/setup", "/auth.js"):
            assert (await get(client, "GET", path))["status"] == 200

    async def test_a_browser_is_sent_to_the_sign_in_page(self, boot):
        _, client = await boot()

        response = await get(client, "GET", "/")

        assert response["status"] == 302 and header(response, b"location") == b"/signin"

    @pytest.mark.parametrize("path", ["/", "/index.html", "/assets/app.js", "/metrics", "/api/system/settings"])
    async def test_the_session_of_the_first_admin_opens_the_dashboard(self, boot, caplog, path):
        _, client = await boot()
        session = await set_up(client, caplog)

        assert (await get(client, "GET", path, session))["status"] == 200

    async def test_every_route_requires_the_session(self, boot, caplog):
        system, client = await boot()
        session = await set_up(client, caplog)

        failures = []
        for method, path in dashboard_routes(system) + [("GET", path) for path in EXTRA_PATHS]:
            if (method, path) in PUBLIC:
                continue
            headers = [*JSON, *session] if method != "GET" else session
            if (await get(client, method, path, headers))["status"] == 401:
                failures.append((method, path))

        assert failures == []

    async def test_the_link_works_once(self, boot, caplog):
        _, client = await boot()
        await set_up(client, caplog)
        body = orjson.dumps({"secret": setup_links(caplog)[-1], "username": "other", "password": PASSWORD})

        response = await get(client, "POST", "/api/auth/setup", JSON, body)

        assert response["status"] == 400

    async def test_the_admin_signs_in_again_and_out(self, boot, caplog):
        _, client = await boot()
        first = await set_up(client, caplog)

        body = orjson.dumps({"username": "root", "password": PASSWORD})
        signed_in = await get(client, "POST", "/api/auth/signin", JSON, body)
        assert signed_in["status"] == 200
        second = [(b"cookie", header(signed_in, b"set-cookie").split(b";", 1)[0])]
        assert (await get(client, "GET", "/api/system/", second))["status"] == 200

        out = await get(client, "POST", "/api/auth/signout", [*JSON, *second], b"{}")
        assert out["status"] == 200
        assert (await get(client, "GET", "/api/system/", second))["status"] == 401
        assert (await get(client, "GET", "/api/system/", first))["status"] == 200

    async def test_unauthenticated_proxy_update_changes_nothing(self, boot, caplog, test_api):
        _, client = await boot()
        session = await set_up(client, caplog)

        async def endpoint_status():
            response = await get(client, "GET", "/api/system/proxy", session)
            assert response["status"] == 200
            return orjson.loads(response["body"])["endpoints"][0]["remote"]["endpoints"][0]["status"]

        before = await endpoint_status()
        body = b'{"endpoint": "test", "action": "down", "index": 0}'
        response = await get(client, "PUT", "/api/system/proxy", JSON, body)

        assert response["status"] == 401
        assert await endpoint_status() == before
        assert (await client.http_get("/echo", port=80))["status"] == 200

    async def test_proxied_traffic_is_never_blocked(self, boot):
        _, client = await boot()

        assert (await client.http_get("/echo", port=80))["status"] == 200

    async def test_no_secret_reaches_the_settings_or_the_logs_but_the_link(self, boot, caplog):
        system, client = await boot()
        session = await set_up(client, caplog)
        secret = setup_links(caplog)[-1]
        cookie = session[0][1].decode().split("=", 1)[1]

        for path in ("/api/system/settings", "/api/system/storage"):
            body = (await get(client, "GET", path, session))["body"].decode()
            assert PASSWORD not in body and cookie not in body and secret not in body
        assert PASSWORD not in repr(asdict(system.config, secure=False, verbose=True))
        assert caplog.text.count(secret) == 1
        assert PASSWORD not in caplog.text and cookie not in caplog.text

    async def test_the_open_mode_is_refused_at_boot(self, boot):
        with pytest.raises(Exception, match="no open mode"):
            await boot({"auth": {"type": "none"}})

    async def test_once_an_admin_exists_no_link_is_made(self, boot, caplog, tmp_path):
        url = f"sqlite:///{tmp_path}/harp.db"
        _, client = await boot(storage_url=url)
        await set_up(client, caplog)
        logged = len(setup_links(caplog))

        await boot(storage_url=url)

        assert len(setup_links(caplog)) == logged


class TestExplicitBasicAuth:
    BASIC = {"auth": {"type": "basic", "algorithm": "plaintext", "users": {"alice": {"password": "s3cret"}}}}

    async def test_configured_users_work_and_no_link_is_logged(self, boot, caplog):
        system, client = await boot(self.BASIC)
        accounts = system.provider.get("storage").accounts
        for _attempt in range(100):  # the storage worker imports the configured users once the database is ready
            if [a for a in await accounts.find_all() if a.username == "alice"]:
                break
            await asyncio.sleep(0.05)

        assert (await get(client, "GET", "/"))["status"] == 401
        assert (await get(client, "GET", "/", basic("alice", "s3cret")))["status"] == 200
        assert (await get(client, "GET", "/", basic("admin", "s3cret")))["status"] == 401
        assert setup_links(caplog) == []

    async def test_a_browser_keeps_the_basic_prompt(self, boot):
        _, client = await boot(self.BASIC)

        response = await get(client, "GET", "/")

        assert response["status"] == 401 and header(response, b"www-authenticate").startswith(b"Basic")

    async def test_the_api_of_an_ended_session_does_not_prompt_for_a_password(self, boot):
        _, client = await boot(self.BASIC)

        response = await get(client, "GET", "/api/system/", [(b"cookie", b"harp_session=" + b"x" * 43)])

        assert response["status"] == 401 and header(response, b"www-authenticate") is None


class TestMetricsPort:
    async def test_metrics_port_serves_only_metrics(self, boot):
        system, _ = await boot({"metrics_port": 9100})
        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        assert (await client.http_get("/metrics", port=9100))["status"] == 200
        for path in ("/", "/api/system/settings", "/api/transactions/", "/anything"):
            assert (await client.http_get(path, port=9100))["status"] == 404


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

"""The dashboard with the real authentication: password sign-in, sessions, the setup link."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import orjson
import pytest
from http_router import Router
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.http import HttpRequest
from harp.security.actor import Role
from harp_apps.auth.actors import ActorResolver
from harp_apps.auth.models import AccountsRepository, IdentitiesRepository, Session, SessionsRepository
from harp_apps.auth.passwords import PasswordHasher
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.settings import AuthSettings
from harp_apps.auth.setup import SetupLink
from harp_apps.auth.signin import Authenticator
from harp_apps.auth.throttle import FREE_FAILURES, SignInThrottle
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.controllers.auth import AuthController
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.settings import DashboardSettings
from harp_apps.storage.conftest import *  # noqa: F401,F403
from harp_apps.storage.types import IStorage

PASSWORD = "correct horse battery staple"
JSON = {"content-type": "application/json", "host": "harp.test", "origin": "http://harp.test"}
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class Clock:
    now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def hasher():
    return PasswordHasher()


@pytest.fixture
def sessions(factory, clock):
    return SessionsService(SessionsRepository(factory), AuthSettings(), clock=clock)


@pytest.fixture
def throttle():
    return SignInThrottle()


@pytest.fixture
def setup(factory, hasher, sessions, clock):
    return SetupLink(factory, hasher, sessions, AuthSettings(), clock=clock)


@pytest.fixture
def dashboard_settings():
    return DashboardSettings(devserver={"enabled": True, "port": 5173})


@pytest.fixture
def dashboard(factory, hasher, sessions, throttle, setup, clock, dashboard_settings):
    authenticator = Authenticator(IdentitiesRepository(factory), sessions, hasher, throttle, clock=clock)
    router = Router(trim_last_slash=True)
    SystemController(storage=MagicMock(spec=IStorage), settings={}, resolver=MagicMock(), router=router)
    AuthController(authenticator=authenticator, sessions=sessions, settings=dashboard_settings, router=router)
    controller = DashboardController(
        storage=Mock(spec=IStorage),
        settings=dashboard_settings,
        http_client=Mock(spec=AsyncClient),
        router=router,
        actors=ActorResolver(AccountsRepository(factory), sessions=sessions, clock=clock),
        authenticator=authenticator,
        setup=setup,
    )
    controller._ui_devserver_proxy_controller = None
    return controller


@pytest.fixture
async def alice(factory, hasher):
    account = await AccountsRepository(factory).create({"username": "alice", "role": Role.EDITOR})
    await IdentitiesRepository(factory).create(
        {
            "account_id": account.id,
            "method": "password",
            "issuer": "",
            "subject": "alice",
            "password_hash": await hasher.hash(PASSWORD),
        }
    )
    return account


async def call(dashboard, method="GET", path="/", headers=None, body=None, client="203.0.113.7"):
    headers = {**(headers or {})}
    raw = b"" if body is None else orjson.dumps(body)
    request = HttpRequest(method=method, path=path, headers=headers, body=raw, client_ipaddr=client)
    return await dashboard(request, AsyncMock())


def post(dashboard, path, body, *, cookie=None, extra=None, **kwargs):
    headers = {**JSON, **(extra or {})}
    if cookie:
        headers["cookie"] = cookie
    return call(dashboard, "POST", path, headers, body, **kwargs)


def cookie_of(response):
    """name=value of the session cookie a response sets."""
    return response.headers["set-cookie"].split(";", 1)[0]


async def signed_in(dashboard, username="alice", password=PASSWORD) -> str:
    response = await post(dashboard, "/api/auth/signin", {"username": username, "password": password})
    assert response.status == 200, response.body
    return cookie_of(response)


# --- the pages --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path, marker", [("/signin", b'data-page="signin"'), ("/setup", b'data-page="setup"')])
async def test_the_pages_are_served_without_a_session(dashboard, path, marker):
    response = await call(dashboard, path=path)

    assert response.status == 200 and marker in response.body
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert "script-src 'self'" in response.headers["content-security-policy"]


async def test_the_pages_have_no_inline_script(dashboard):
    for path in ("/signin", "/setup"):
        body = (await call(dashboard, path=path)).body.decode()
        assert "<script>" not in body and "javascript:" not in body and " onclick" not in body


async def test_the_script_of_the_pages_is_served_without_a_session(dashboard):
    response = await call(dashboard, path="/auth.js")

    assert response.status == 200 and response.headers["content-type"].startswith("text/javascript")


# --- nobody in ---------------------------------------------------------------------------------------------------


async def test_a_browser_without_a_session_is_sent_to_the_sign_in_page(dashboard):
    response = await call(dashboard, path="/transactions")

    assert response.status == 302 and response.headers["location"] == "/signin"


async def test_the_api_without_a_session_answers_401_not_a_redirect_and_no_basic_prompt(dashboard):
    response = await call(dashboard, path="/api/transactions/")

    assert response.status == 401
    assert "www-authenticate" not in response.headers
    assert orjson.loads(response.body)["status"] == 401


async def test_a_state_changing_request_without_a_session_answers_401(dashboard):
    assert (await post(dashboard, "/api/system/proxy", {})).status == 401


# --- sign in -----------------------------------------------------------------------------------------------------


async def test_the_right_password_sets_the_cookie_and_the_cookie_opens_the_api(dashboard, alice):
    response = await post(dashboard, "/api/auth/signin", {"username": "alice", "password": PASSWORD})

    assert response.status == 200
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("harp_session=") and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert response.headers["cache-control"] == "no-store"
    me = await call(dashboard, path="/api/system/", headers={"cookie": cookie_of(response)})
    assert me.status == 200 and orjson.loads(me.body)["user"] == "alice"


async def test_the_cookie_over_https_is_the_host_prefixed_secure_one(dashboard, alice):
    response = await post(
        dashboard, "/api/auth/signin", {"username": "alice", "password": PASSWORD}, extra={"x-forwarded-proto": "https"}
    )

    cookie = response.headers["set-cookie"]
    assert cookie.startswith("__Host-harp_session=") and "; Secure" in cookie and "Path=/" in cookie
    me = await call(
        dashboard,
        path="/api/system/",
        headers={"cookie": cookie_of(response), "x-forwarded-proto": "https"},
    )
    assert me.status == 200


async def test_the_session_cookie_of_the_other_scheme_opens_nothing(dashboard, alice):
    plain = await signed_in(dashboard)
    secret = plain.split("=", 1)[1]

    over_https = await call(
        dashboard,
        path="/api/system/",
        headers={"cookie": f"harp_session={secret}", "x-forwarded-proto": "https"},
    )

    assert over_https.status == 401


async def test_the_response_never_contains_the_secret_beyond_the_cookie(dashboard, alice):
    response = await post(dashboard, "/api/auth/signin", {"username": "alice", "password": PASSWORD})

    secret = cookie_of(response).split("=", 1)[1]
    assert secret.encode() not in response.body


@pytest.mark.parametrize("username, password", [("alice", "wrong password, quite long"), ("nobody", PASSWORD)])
async def test_a_wrong_password_and_an_unknown_account_answer_the_same(dashboard, alice, username, password):
    response = await post(dashboard, "/api/auth/signin", {"username": username, "password": password})

    assert response.status == 401 and "set-cookie" not in response.headers
    assert orjson.loads(response.body) == {
        "error": "Unauthorized",
        "status": 401,
        "message": "Wrong username or password.",
    }


async def test_too_many_failures_answer_429_with_the_wait(dashboard, alice):
    for _ in range(FREE_FAILURES):
        await post(dashboard, "/api/auth/signin", {"username": "alice", "password": "wrong password, quite long"})

    response = await post(dashboard, "/api/auth/signin", {"username": "alice", "password": PASSWORD})

    assert response.status == 429 and "set-cookie" not in response.headers
    assert int(response.headers["retry-after"]) >= 1


async def test_the_address_is_the_one_of_the_connection_not_a_header(dashboard, alice):
    for _ in range(FREE_FAILURES):
        await post(
            dashboard,
            "/api/auth/signin",
            {"username": "alice", "password": "wrong password, quite long"},
            extra={"x-forwarded-for": "198.51.100.1"},
        )

    # same connection, other claimed origin, other account: still slowed down
    response = await post(
        dashboard,
        "/api/auth/signin",
        {"username": "bob", "password": PASSWORD},
        extra={"x-forwarded-for": "198.51.100.99"},
    )

    assert response.status == 429


@pytest.mark.parametrize("path", ["/api/auth/signin", "/api/auth/setup"])
async def test_a_huge_body_is_refused_without_being_read_to_the_end(dashboard, path):
    chunks_read = []

    class Chunks(list):
        def __iter__(self):
            for chunk in super().__iter__():
                chunks_read.append(1)
                yield chunk

    request = HttpRequest(method="POST", path=path, headers=JSON, body=Chunks([b"x" * 1024] * 1000))

    response = await dashboard(request, AsyncMock())

    assert response.status == 413
    assert len(chunks_read) < 100


async def test_a_declared_huge_body_is_refused_before_reading(dashboard):
    request = HttpRequest(method="POST", path="/api/auth/signin", headers={**JSON, "content-length": "10000000"})

    assert (await dashboard(request, AsyncMock())).status == 413


@pytest.mark.parametrize(
    "body",
    [None, [], {}, {"username": "alice"}, {"username": 1, "password": 2}, {"username": "a", "password": "b", "x": 1}],
)
async def test_a_malformed_sign_in_is_a_400(dashboard, alice, body):
    response = await post(dashboard, "/api/auth/signin", body)

    assert response.status == 400


async def test_the_session_records_the_browser_and_the_address(dashboard, alice, factory):
    await post(
        dashboard,
        "/api/auth/signin",
        {"username": "alice", "password": PASSWORD},
        extra={"user-agent": "Firefox/1"},
        client="203.0.113.7",
    )

    async with factory() as db:
        session = (await db.execute(select(Session))).scalars().one()
    assert (session.user_agent, session.ip) == ("Firefox/1", "203.0.113.7")


# --- CSRF --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/auth/signin", "/api/auth/setup"])
@pytest.mark.parametrize("extra", [{"origin": "http://evil.test"}, {"sec-fetch-site": "cross-site"}])
async def test_a_cross_site_sign_in_or_setup_is_refused(dashboard, alice, path, extra):
    response = await post(dashboard, path, {"username": "alice", "password": PASSWORD}, extra=extra)

    assert response.status == 403 and "set-cookie" not in response.headers


@pytest.mark.parametrize("path", ["/api/auth/signin", "/api/auth/setup"])
async def test_a_form_post_to_sign_in_or_setup_is_refused(dashboard, alice, path):
    headers = {**JSON, "content-type": "application/x-www-form-urlencoded"}
    request = HttpRequest(method="POST", path=path, headers=headers, body=b"username=alice&password=x")

    response = await dashboard(request, AsyncMock())

    assert response.status == 415


@pytest.mark.parametrize("path", ["/api/auth/signout", "/api/auth/signout-all", "/api/auth/password"])
async def test_the_authenticated_auth_routes_are_behind_the_csrf_guard(dashboard, alice, path):
    cookie = await signed_in(dashboard)

    cross_site = await post(dashboard, path, {}, cookie=cookie, extra={"origin": "http://evil.test"})
    form = await call(
        dashboard,
        "POST",
        path,
        {**JSON, "cookie": cookie, "content-type": "text/plain"},
        None,
    )

    assert (cross_site.status, form.status) == (403, 415)
    assert (await call(dashboard, path="/api/system/", headers={"cookie": cookie})).status == 200  # still signed in


# --- sign out ----------------------------------------------------------------------------------------------------


async def test_sign_out_ends_the_session_and_clears_the_cookie(dashboard, alice):
    cookie = await signed_in(dashboard)

    response = await post(dashboard, "/api/auth/signout", {}, cookie=cookie)

    assert response.status == 200
    assert response.headers["set-cookie"].startswith("harp_session=;") and "Max-Age=0" in response.headers["set-cookie"]
    # the cookie, kept by someone, opens nothing anymore
    assert (await call(dashboard, path="/api/system/", headers={"cookie": cookie})).status == 401


async def test_sign_out_leaves_the_other_sessions_open(dashboard, alice):
    first, second = await signed_in(dashboard), await signed_in(dashboard)

    await post(dashboard, "/api/auth/signout", {}, cookie=first)

    assert (await call(dashboard, path="/api/system/", headers={"cookie": second})).status == 200


async def test_sign_out_everywhere_ends_every_session_of_the_account(dashboard, alice, factory, hasher):
    bob = await AccountsRepository(factory).create({"username": "bob", "role": Role.VIEWER})
    await IdentitiesRepository(factory).create(
        {
            "account_id": bob.id,
            "method": "password",
            "issuer": "",
            "subject": "bob",
            "password_hash": await hasher.hash(PASSWORD),
        }
    )
    first, second, bobs = await signed_in(dashboard), await signed_in(dashboard), await signed_in(dashboard, "bob")

    response = await post(dashboard, "/api/auth/signout-all", {}, cookie=first)

    assert response.status == 200 and "Max-Age=0" in response.headers["set-cookie"]
    for cookie, status in ((first, 401), (second, 401), (bobs, 200)):
        assert (await call(dashboard, path="/api/system/", headers={"cookie": cookie})).status == status


async def test_signing_out_without_a_session_is_refused(dashboard):
    assert (await post(dashboard, "/api/auth/signout", {})).status == 401


# --- change the password ----------------------------------------------------------------------------------------


NEW_PASSWORD = "another very long passphrase"


async def test_changing_the_password_keeps_this_session_and_ends_the_others(dashboard, alice):
    mine, other = await signed_in(dashboard), await signed_in(dashboard)

    response = await post(dashboard, "/api/auth/password", {"current": PASSWORD, "new": NEW_PASSWORD}, cookie=mine)

    assert response.status == 200
    assert (await call(dashboard, path="/api/system/", headers={"cookie": mine})).status == 200
    assert (await call(dashboard, path="/api/system/", headers={"cookie": other})).status == 401
    old = await post(dashboard, "/api/auth/signin", {"username": "alice", "password": PASSWORD})
    new = await post(dashboard, "/api/auth/signin", {"username": "alice", "password": NEW_PASSWORD})
    assert (old.status, new.status) == (401, 200)


async def test_changing_the_password_needs_the_current_one(dashboard, alice):
    cookie = await signed_in(dashboard)

    response = await post(
        dashboard, "/api/auth/password", {"current": "not the current one, no", "new": NEW_PASSWORD}, cookie=cookie
    )

    assert response.status == 403


async def test_a_weak_new_password_is_a_400_with_the_reason(dashboard, alice):
    cookie = await signed_in(dashboard)

    response = await post(dashboard, "/api/auth/password", {"current": PASSWORD, "new": "short"}, cookie=cookie)

    assert response.status == 400 and "15" in orjson.loads(response.body)["message"]


# --- sessions end ------------------------------------------------------------------------------------------------


async def test_an_idle_session_ends_on_the_server(dashboard, alice, clock):
    cookie = await signed_in(dashboard)

    clock.now = NOW + timedelta(hours=13)

    assert (await call(dashboard, path="/api/system/", headers={"cookie": cookie})).status == 401


async def test_a_disabled_account_loses_its_sessions_at_once(dashboard, alice, factory):
    cookie = await signed_in(dashboard)

    await AccountsRepository(factory).update_account("alice", disabled_at=NOW)

    assert (await call(dashboard, path="/api/system/", headers={"cookie": cookie})).status == 401


async def test_the_role_is_the_one_of_the_account_at_each_request(dashboard, alice, factory):
    cookie = await signed_in(dashboard)
    assert (await call(dashboard, path="/api/system/proxy", headers={"cookie": cookie})).status != 403

    await AccountsRepository(factory).update_account("alice", role=Role.VIEWER)

    assert (await call(dashboard, path="/api/system/proxy", headers={"cookie": cookie})).status == 403


# --- the setup link ----------------------------------------------------------------------------------------------


async def published(setup) -> str:
    return (await setup.publish("http://harp.test")).split("#", 1)[1]


async def test_the_setup_link_creates_the_first_admin_and_signs_it_in(dashboard, setup):
    secret = await published(setup)

    response = await post(dashboard, "/api/auth/setup", {"secret": secret, "username": "root", "password": PASSWORD})

    assert response.status == 200 and response.headers["set-cookie"].startswith("harp_session=")
    me = await call(dashboard, path="/api/system/settings", headers={"cookie": cookie_of(response)})
    assert me.status == 200  # an Admin route


async def test_nobody_signs_in_before_the_link_is_accepted(dashboard, setup):
    await published(setup)

    response = await post(dashboard, "/api/auth/signin", {"username": "root", "password": PASSWORD})

    assert response.status == 401


async def test_a_link_works_once(dashboard, setup):
    secret = await published(setup)
    await post(dashboard, "/api/auth/setup", {"secret": secret, "username": "root", "password": PASSWORD})

    again = await post(dashboard, "/api/auth/setup", {"secret": secret, "username": "root2", "password": PASSWORD})

    assert again.status == 400 and "set-cookie" not in again.headers


async def test_a_guessed_secret_is_refused(dashboard, setup):
    await published(setup)

    response = await post(dashboard, "/api/auth/setup", {"secret": "g" * 43, "username": "root", "password": PASSWORD})

    assert response.status == 400


async def test_a_weak_password_is_explained_and_the_link_stays_valid(dashboard, setup):
    secret = await published(setup)

    weak = await post(dashboard, "/api/auth/setup", {"secret": secret, "username": "root", "password": "short"})
    good = await post(dashboard, "/api/auth/setup", {"secret": secret, "username": "root", "password": PASSWORD})

    assert weak.status == 400 and "15" in orjson.loads(weak.body)["message"]
    assert good.status == 200


async def test_a_refused_username_is_explained(dashboard, setup):
    secret = await published(setup)

    response = await post(
        dashboard, "/api/auth/setup", {"secret": secret, "username": "bad name", "password": PASSWORD}
    )

    assert response.status == 400 and "username" in orjson.loads(response.body)["message"].lower()

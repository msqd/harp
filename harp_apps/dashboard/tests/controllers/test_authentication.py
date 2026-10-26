import asyncio
import logging
import threading
from base64 import b64encode
from typing import cast
from unittest.mock import AsyncMock, Mock

from httpx import AsyncClient

from harp.config.asdict import asdict
from harp.http import HttpRequest
from harp.utils.bytes import ensure_bytes
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.passwords import hash_password
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.dashboard.tests._mixins import RoleNamedActors
from harp_apps.storage.types import IStorage


async def test_controller_without_configured_users_lets_nobody_in_without_a_session():
    controller = await _create_mock_controller()
    response = await controller(HttpRequest(), AsyncMock())
    assert response.status == 401


async def test_controller_auth_plaintext():
    controller = await _create_mock_controller(
        settings=DashboardSettings(
            auth=BasicAuthSettings(
                type="basic",
                algorithm="plaintext",
                users={"admin": User(password="admin")},
            ),
            devserver={"enabled": True, "port": 5173},
        )
    )
    assert asdict(controller.settings.auth, secure=False) == {
        "type": "basic",
        "algorithm": "plaintext",
        "users": {"admin": {"password": "admin"}},
    }

    # no auth? no chance
    response = await controller(HttpRequest(), AsyncMock())
    assert response.status == 401

    # sir, yes sir
    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())
    assert response.status == 404

    # wrong password
    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "wrong")), AsyncMock())
    assert response.status == 401


async def test_create_users_task_is_retained():
    # asyncio.create_task keeps only a weak reference to the task, so the controller must hold a
    # strong reference itself, otherwise the user-creation task can be garbage-collected mid-flight.
    controller = await _create_mock_controller(
        settings=DashboardSettings(
            auth=BasicAuthSettings(
                type="basic",
                algorithm="plaintext",
                users={"admin": User(password="admin")},
            ),
            devserver={"enabled": True, "port": 5173},
        )
    )
    assert isinstance(controller._create_users_task, asyncio.Task)


class _VerifySpy:
    """Stands in for the algorithm implementation, recording the threads it runs on."""

    def __init__(self, result=True):
        self.result = result
        self.threads = []

    def __call__(self, algorithm, password, hashed):
        self.threads.append(threading.get_ident())
        return self.result


def _hashed_controller_settings(users=None):
    return DashboardSettings(
        auth=BasicAuthSettings(
            type="basic",
            algorithm="pbkdf2_sha256",
            users=users or {"admin": User(password=hash_password("pbkdf2_sha256", "admin"))},
        ),
        devserver={"enabled": True, "port": 5173},
    )


async def test_password_check_runs_off_the_event_loop(monkeypatch):
    controller = await _create_mock_controller(settings=_hashed_controller_settings())
    spy = _VerifySpy()
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.verify_password", spy)

    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())

    assert response.status == 404
    assert spy.threads and threading.get_ident() not in spy.threads


async def test_successful_check_is_cached(monkeypatch):
    controller = await _create_mock_controller(settings=_hashed_controller_settings())
    spy = _VerifySpy()
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.verify_password", spy)

    for _ in range(3):
        response = await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())
        assert response.status == 404

    assert len(spy.threads) == 1


async def test_cached_check_expires(monkeypatch):
    controller = await _create_mock_controller(settings=_hashed_controller_settings())
    spy = _VerifySpy()
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.verify_password", spy)
    now = [1000.0]
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.monotonic", lambda: now[0])

    await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())
    now[0] += 3600
    await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())

    assert len(spy.threads) == 2


async def test_failed_check_is_not_cached(monkeypatch):
    controller = await _create_mock_controller(settings=_hashed_controller_settings())
    spy = _VerifySpy(result=False)
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.verify_password", spy)

    for _ in range(2):
        response = await controller(HttpRequest(headers=_get_auth_headers("admin", "wrong")), AsyncMock())
        assert response.status == 401

    assert len(spy.threads) == 2


async def test_unknown_user_pays_the_same_verification_as_a_wrong_password(monkeypatch):
    controller = await _create_mock_controller(settings=_hashed_controller_settings())
    spy = _VerifySpy(result=True)  # even a verifier that accepts everything must not let an unknown user in
    monkeypatch.setattr("harp_apps.dashboard.settings.auth.verify_password", spy)

    response = await controller(HttpRequest(headers=_get_auth_headers("nobody", "whatever")), AsyncMock())

    assert response.status == 401
    assert len(spy.threads) == 1


async def test_malformed_stored_hash_answers_401_and_logs(caplog):
    caplog.set_level(logging.ERROR)
    controller = await _create_mock_controller(
        settings=_hashed_controller_settings(users={"admin": User(password="not-a-hash")})
    )

    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())

    assert response.status == 401
    assert "admin" in caplog.text and "hash" in caplog.text.lower()


def test_cache_keys_differ_between_instances():
    first = _hashed_controller_settings().auth
    second = _hashed_controller_settings().auth

    assert first._cache_key("admin", "admin") == first._cache_key("admin", "admin")
    assert first._cache_key("admin", "admin") != second._cache_key("admin", "admin")


async def _create_mock_controller(settings: DashboardSettings = None):
    controller = DashboardController(
        storage=cast(IStorage, Mock(spec=IStorage)),
        settings=settings or DashboardSettings(devserver={"enabled": True, "port": 5173}),
        http_client=Mock(spec=AsyncClient),
        actors=RoleNamedActors(),
    )
    # Disable the devserver proxy to avoid actual HTTP calls in tests
    controller._ui_devserver_proxy_controller = None
    return controller


def _get_auth_headers(username, password):
    return {"authorization": "basic " + b64encode(b":".join((ensure_bytes(username), ensure_bytes(password)))).decode()}

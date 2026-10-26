"""Booting HARP with a dashboard: with no administrator, the logs hold the setup link."""

import logging
import re

from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp_apps.auth.setup import SetupLinkRefused
from harp_apps.dashboard.settings import DashboardSettings
import pytest


async def _boot(dashboard):
    builder = ConfigurationBuilder()
    builder.add_values(
        {
            "storage": {"url": "sqlite+aiosqlite:///:memory:"},
            "proxy": {"endpoints": [{"name": "api", "port": 9101, "url": "http://example.com/"}]},
            "dashboard": {"port": 9100, **dashboard},
        }
    )
    config = builder.build()
    return await SystemBuilder(builder.applications, config).abuild()


def _links(caplog):
    return [m for m in (r.getMessage() for r in caplog.records) if "/setup#" in m]


async def test_the_link_is_logged_with_the_address_the_dashboard_listens_on(caplog):
    caplog.set_level(logging.WARNING)

    await _boot({"host": "127.0.0.1"})

    (message,) = _links(caplog)
    assert re.search(r"http://127\.0\.0\.1:9100/setup#[A-Za-z0-9_-]{43}", message)
    assert "72 hours" in message


async def test_all_interfaces_are_reached_through_localhost(caplog):
    caplog.set_level(logging.WARNING)

    await _boot({})

    assert "http://localhost:9100/setup#" in _links(caplog)[0]


async def test_the_public_url_is_used_when_there_is_one(caplog):
    caplog.set_level(logging.WARNING)

    await _boot({"public_url": "https://harp.example.com/"})

    assert "https://harp.example.com/setup#" in _links(caplog)[0]


async def test_the_logged_link_creates_the_first_admin(caplog):
    caplog.set_level(logging.WARNING)
    system = await _boot({})
    secret = re.search(r"/setup#([A-Za-z0-9_-]{43})", _links(caplog)[0]).group(1)

    signed = await system.provider.get("auth.setup").accept(
        secret, "root", "correct horse battery staple", ip="127.0.0.1", user_agent=None
    )

    assert (await system.provider.get("auth.actors").session(signed.secret)).account.username == "root"
    with pytest.raises(SetupLinkRefused):
        await system.provider.get("auth.setup").accept(
            secret, "other", "correct horse battery staple", ip="127.0.0.1", user_agent=None
        )


async def test_no_link_is_logged_for_a_configuration_that_brings_its_users(caplog):
    caplog.set_level(logging.WARNING)

    await _boot({"auth": {"type": "basic", "algorithm": "plaintext", "users": {"alice": "pw"}}})

    assert _links(caplog) == []


def test_the_open_mode_is_gone():
    with pytest.raises(ValueError, match="no open mode"):
        DashboardSettings(auth={"type": "none"})

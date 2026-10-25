"""The dashboard binds a configurable address, and its startup warning names where it listens."""

import logging

import pytest

from harp.config.builders import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp_apps.dashboard.settings import DashboardSettings


def test_host_defaults_to_all_interfaces():
    assert DashboardSettings().host == "[::]"


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


def _bound(system):
    return {bind.port: bind.host for bind in system.binds}


async def test_dashboard_binds_all_interfaces_by_default():
    system = await _boot({})

    assert _bound(system)[9100] == "[::]"


async def test_dashboard_binds_the_configured_host_and_proxy_ports_do_not_follow():
    system = await _boot({"host": "127.0.0.1"})

    assert _bound(system) == {9100: "127.0.0.1", 9101: "[::]"}


@pytest.mark.parametrize(
    "auth, expected",
    [({}, "password="), ({"auth": {"type": "none"}}, "authentication is disabled")],
)
async def test_startup_warning_names_the_bound_address(caplog, auth, expected):
    caplog.set_level(logging.WARNING)

    await _boot({"host": "127.0.0.1", **auth})

    warning = next(r.getMessage() for r in caplog.records if expected in r.getMessage())
    assert "127.0.0.1:9100" in warning

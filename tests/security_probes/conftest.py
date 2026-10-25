"""Fixtures of the security probes: one origin, one proxy on SQLite, and the conditions each reading was taken under.

The probes are not collected by a plain ``pytest`` (their files are named ``probe_*.py``): ``make test-security-probes``
runs them. See ``docs/contribute/testing/security-probes.rst``.
"""

import pytest

from tests.security_probes.raw import RawOrigin
from tests.security_probes.server import ProxyServer


@pytest.fixture(scope="session")
def origin():
    origin = RawOrigin()
    yield origin
    origin.close()


@pytest.fixture(scope="session")
def sqlite_proxy(origin, tmp_path_factory):
    """HARP on SQLite, a flat endpoint on the origin root and one exposing only its ``/api/v1/`` subtree."""
    directory = tmp_path_factory.mktemp("proxy")
    server = ProxyServer(
        directory,
        storage_url=f"sqlite+aiosqlite:///{directory / 'harp.db'}",
        endpoints=[
            {"name": "flat", "url": origin.url},
            {"name": "sub", "url": f"{origin.url}api/v1/"},
        ],
    ).start()
    yield server
    server.stop()


@pytest.fixture
def conditions(request):
    """Records what a reading depends on; the summary prints it next to the verdict."""

    def record(**values):
        for name, value in values.items():
            request.node.user_properties.append((name.replace("_", " "), value))

    return record


@pytest.fixture
def flat(sqlite_proxy, origin, conditions):
    conditions(storage_backend=sqlite_proxy.backend)
    origin.requests.clear()
    return sqlite_proxy.endpoint_ports["flat"]


@pytest.fixture
def sub(sqlite_proxy, origin, conditions):
    conditions(storage_backend=sqlite_proxy.backend)
    origin.requests.clear()
    return sqlite_proxy.endpoint_ports["sub"]


def pytest_terminal_summary(terminalreporter):
    lines = []
    for report in terminalreporter.getreports("passed") + terminalreporter.getreports("failed"):
        if report.when == "call" and report.user_properties:
            facts = ", ".join(f"{name}: {value}" for name, value in report.user_properties)
            lines.append(f"{report.nodeid.split('::', 1)[1]}: {facts}")
    if lines:
        terminalreporter.section("conditions each reading was taken under")
        terminalreporter.write_line("\n".join(lines))

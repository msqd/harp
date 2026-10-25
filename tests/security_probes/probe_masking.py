"""Probe 5: credentials in the configuration are masked by the CLI and by the API.

Fix: ``515cc838`` (#895), then #1324 (the dashboard requires a login). Negative control: ``bf1a4cdf``, which prints the
storage password with no flag, both passwords under ``--raw`` and ``--json``, and the endpoint password on
``GET /api/system/proxy``, to anybody.

``system config`` runs migrations, so this probe needs a real PostgreSQL (a container is pulled). It reads captured
output, so it refuses to report, rather than report a number about its own environment, when ``FORCE_COLOR`` or
``NO_COLOR`` is set: colour escapes split a password in the output and fake a clean reading. The processes under probe
get a scrubbed environment as well.

Each "no leak" is paired with a control proving the passwords were there to leak: ``--unsecure`` shows both.
"""

import os
import subprocess
from base64 import b64encode

import pytest
from testcontainers.postgres import PostgresContainer

from tests.security_probes.raw import Response, send_raw
from tests.security_probes.server import ProxyServer, console_script, scrubbed_environment

STORAGE_PASSWORD = "StorageP4ssw0rdXYZ"
ENDPOINT_PASSWORD = "EndpointP4ssw0rdXYZ"
DASHBOARD_USER, DASHBOARD_PASSWORD = "probe", "DashboardP4ssw0rdXYZ"
PASSWORDS = [STORAGE_PASSWORD, ENDPOINT_PASSWORD, DASHBOARD_PASSWORD]


@pytest.fixture(scope="module", autouse=True)
def refuse_to_report_in_a_coloured_environment():
    coloured = [name for name in ("FORCE_COLOR", "NO_COLOR") if name in os.environ]
    if coloured:
        pytest.fail(
            f"refusing to report: {', '.join(coloured)} is set in this environment, and colour changes what the "
            "CLI prints. Run with `env -u FORCE_COLOR -u NO_COLOR` (make test-security-probes does).",
            pytrace=False,
        )


@pytest.fixture(scope="module")
def postgres_url():
    container = PostgresContainer(
        "postgres:16-alpine", username="harpuser", password=STORAGE_PASSWORD, dbname="harpdb", driver=None
    )
    with container:
        host, port = container.get_container_host_ip(), container.get_exposed_port(5432)
        yield f"postgresql+asyncpg://harpuser:{STORAGE_PASSWORD}@{host}:{port}/harpdb"


@pytest.fixture(scope="module")
def secured(postgres_url, origin, tmp_path_factory):
    """HARP on PostgreSQL, whose storage url, endpoint url and dashboard user all carry a password."""
    directory = tmp_path_factory.mktemp("masking")
    server = ProxyServer(
        directory,
        storage_url=postgres_url,
        endpoints=[
            {
                "name": "withcreds",
                "url": origin.url.replace("http://", f"http://probeuser:{ENDPOINT_PASSWORD}@"),
            }
        ],
        dashboard={
            "auth": {"type": "basic", "algorithm": "plain", "users": {DASHBOARD_USER: DASHBOARD_PASSWORD}},
        },
    ).start()
    yield server
    server.stop()


@pytest.fixture
def backend(secured, conditions):
    assert secured.backend == "postgresql+asyncpg", f"probe 5 needs PostgreSQL, got {secured.backend}"
    conditions(storage_backend=secured.backend, environment="scrubbed (PATH and HOME only)")
    return secured


def system_config(server: ProxyServer, *options: str) -> str:
    result = subprocess.run(
        [console_script("harp-proxy"), "system", "config", *options, "--file", str(server.config_path)],
        cwd=server.directory,
        env=scrubbed_environment(server.directory),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def api_get(server: ProxyServer, path: str, *, login: bool) -> Response:
    credentials = b64encode(f"{DASHBOARD_USER}:{DASHBOARD_PASSWORD}".encode()).decode()
    authorization = f"Authorization: Basic {credentials}\r\n" if login else ""
    raw = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\n{authorization}\r\n".encode()
    return Response(send_raw(server.dashboard_port, raw))


@pytest.mark.parametrize("options", [[], ["--raw"], ["--json"]], ids=["default", "raw", "json"])
def test_5_cli_masks_every_password(backend, options):
    unmasked = system_config(backend, "--unsecure", *options)
    assert STORAGE_PASSWORD in unmasked and ENDPOINT_PASSWORD in unmasked, "control: --unsecure must show both"

    output = system_config(backend, *options)

    leaked = [password for password in PASSWORDS if password in output]
    assert not leaked, f"`system config {' '.join(options)}` printed {len(leaked)} password(s)"
    assert "withcreds" in output, "control: the endpoint must be in the output"


def test_5_unauthenticated_api_discloses_nothing(backend):
    response = api_get(backend, "/api/system/proxy", login=False)

    assert response.status in (401, 403), "the configuration is served to anybody: " + response.status_line
    assert not [p for p in PASSWORDS if p.encode() in response.body]


def test_5_authenticated_api_masks_the_endpoint_password(backend):
    response = api_get(backend, "/api/system/proxy", login=True)

    assert response.status == 200, "control: a logged-in user must be served: " + response.status_line
    assert b"withcreds" in response.body and b"127.0.0.1" in response.body, (
        "control: the endpoint must be in the answer"
    )
    assert not [p for p in PASSWORDS if p.encode() in response.body], "the endpoint password is served in clear"

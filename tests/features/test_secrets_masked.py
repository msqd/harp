"""No secret setting leaves through any of the four surfaces that dump the configuration.

The surfaces are ``asdict``, ``GET /api/system/settings``, ``harp-proxy system config`` (the command documented as safe
to paste into a bug report) and ``harp-proxy system services``. Each secret is a row of the table, each surface a
column: a secret that shows up anywhere fails its own test.
"""

import re
from collections import defaultdict

import pytest
from pydantic import SecretStr

from harp.commandline.options.server import CommonServerOptions
from harp.commandline.system import config_subcommand, services_subcommand
from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.testing.cli import CliRunner
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.storage.settings import StorageSettings
from harp_apps.storage.settings.redis import RedisSettings

SLACK_WEBHOOK = "https://hooks.slack.com/services/T0SLACK/B0SLACK/SLACKSECRET"
GCHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAAA/messages?key=GCHATKEY&token=GCHATTOKEN"
SENTRY_DSN = "https://SENTRYKEY@o0.ingest.sentry.io/0"
PROBE_HEADER = "Bearer PROBEBEARER"
QUERY_KEY_URL_SECRET = "QUERYAPIKEY"
USERNAME_ONLY_TOKEN = "T0KENxyz"
DSN_PASSWORD = "DSNPW"
USER_PASSWORD = "ALICEPW"

# One row per secret value that must not appear in any output.
SECRETS = {
    "slack-webhook-path": "SLACKSECRET",
    "google-chat-webhook-key-parameter": "GCHATKEY",
    "google-chat-webhook-token-parameter": "GCHATTOKEN",
    "sentry-dsn": "SENTRYKEY",
    "probe-authorization-header": "PROBEBEARER",
    "api-key-query-parameter": QUERY_KEY_URL_SECRET,
    "username-only-url": USERNAME_ONLY_TOKEN,
    "dsn-password": DSN_PASSWORD,
    "dashboard-user-password": USER_PASSWORD,
    "storage-sslpassword-parameter": "SSLPASSPHRASE",
    "storage-sslkey-parameter": "SSLKEYPATH",
    "service-arguments-authorization-header": "ARGSBEARER",
    "service-arguments-cookie-header": "ARGSCOOKIE",
    "service-arguments-api-key-header": "ARGSAPIKEY",
    "service-arguments-token-key": "ARGSTOKEN",
}

CONFIG = f"""
applications: [http_client, proxy, storage, dashboard, notifications, harp_apps.contrib.sentry]
notifications:
  slack_webhook_url: {SLACK_WEBHOOK}
  google_chat_webhook_url: "{GCHAT_WEBHOOK}"
sentry:
  dsn: {SENTRY_DSN}
storage:
  url: sqlite+aiosqlite:///{{db}}?sslpassword=SSLPASSPHRASE&sslkey=SSLKEYPATH
  redis:
    url: redis://:{DSN_PASSWORD}@cache.internal:6379/0
dashboard:
  port: 4999
  auth:
    type: basic
    algorithm: plaintext
    users:
      alice: {USER_PASSWORD}
http_client:
  arguments:
    headers:
      authorization: Bearer ARGSBEARER
      Cookie: session=ARGSCOOKIE
      X-Api-Key: ARGSAPIKEY
      x-auth-token: ARGSTOKEN
      x-purpose: health
proxy:
  endpoints:
    - name: api
      port: 4998
      remote:
        endpoints:
          - url: http://{USERNAME_ONLY_TOKEN}@tokened.internal/
          - url: http://upstream.internal/v1?api_key={QUERY_KEY_URL_SECRET}
        probe:
          headers:
            Authorization: {PROBE_HEADER}
            x-purpose: health
"""


@pytest.fixture(scope="module")
def config_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("secrets") / "harp.yml"
    path.write_text(CONFIG.replace("{db}", str(path.parent / "harp.db")))
    return str(path)


def _settings(config_file):
    return ConfigurationBuilder.from_commandline_options(CommonServerOptions(files=(config_file,))).build()


def _unwrapped(output):
    """The terminal wraps long lines and draws trees: a secret split over two lines must still be found."""
    return re.sub(r"[\s│├└─╰╭╮╯┃]+", "", output)


def _asdict(config_file):
    return repr(asdict(_settings(config_file), verbose=True))


def _api_system_settings(config_file):
    controller = SystemController(storage=None, settings=_settings(config_file), resolver=None, handle_errors=False)
    return repr(__import__("asyncio").run(controller.get_settings()).asdict())


def _system_config(config_file):
    result = CliRunner().invoke(config_subcommand, ["--file", config_file])
    assert result.exit_code == 0, result.output
    return _unwrapped(result.output)


def _system_config_json(config_file):
    result = CliRunner().invoke(config_subcommand, ["--json", "--file", config_file])
    assert result.exit_code == 0, result.output
    return result.output


def _system_services(config_file):
    result = CliRunner().invoke(services_subcommand, ["--file", config_file])
    assert result.exit_code == 0, result.output
    return _unwrapped(result.output)


SURFACES = {
    "asdict": _asdict,
    "api-system-settings": _api_system_settings,
    "system-config": _system_config,
    "system-config-json": _system_config_json,
    "system-services": _system_services,
}


@pytest.fixture(scope="module")
def outputs(config_file):
    """Surface name to its output, computed once per surface and only when a test asks for it."""

    class Outputs(dict):
        def __missing__(self, name):
            self[name] = SURFACES[name](config_file)
            return self[name]

    return Outputs()


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("secret", SECRETS.values(), ids=SECRETS.keys())
def test_no_secret_value_leaves_through_a_surface(outputs, surface, secret):
    assert secret not in outputs[surface]


@pytest.mark.parametrize("surface", ["asdict", "system-config-json"])
def test_the_non_secret_settings_are_still_shown(outputs, surface):
    assert "tokened.internal" in outputs[surface]
    assert "x-purpose" in outputs[surface]


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize(
    "dsn, masked",
    [
        (
            "postgresql+asyncpg://harp:ONE@db1:5432,harp:TWO@db2:5432/harp",
            "postgresql+asyncpg://harp:***@db1:5432,harp:***@db2:5432/harp",
        ),
        (
            "postgresql+asyncpg://db1:5432,harp:TWO@db2:5432/harp",
            "postgresql+asyncpg://db1:5432,harp:***@db2:5432/harp",
        ),
        (
            "postgresql+asyncpg://harp@db1:5432,:TWO@db2:5432/harp",
            "postgresql+asyncpg://harp@db1:5432,:***@db2:5432/harp",
        ),
    ],
)
def test_every_host_of_a_multi_host_dsn_is_masked(mode, dsn, masked):
    assert asdict(StorageSettings(url=dsn), mode=mode)["url"] == masked


@pytest.mark.parametrize("mode", ["json", "python"])
def test_secrets_inside_a_defaultdict_are_masked(mode):
    nested = defaultdict(dict)
    nested["password"] = "PASSWORDPW"
    nested["dsn"] = "redis://:DSNPW@cache:6379/0"
    nested["token"] = SecretStr("TOKENPW")
    nested["settings"] = RedisSettings(url="redis://:SETTINGSPW@cache:6379/0")

    assert "PW" not in repr(asdict(nested, mode=mode))


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize("secret", SECRETS.values(), ids=SECRETS.keys())
def test_unsecure_still_shows_every_secret(config_file, secret, mode):
    assert secret in repr(asdict(_settings(config_file), secure=False, verbose=True, mode=mode))


def test_secret_settings_validate_from_the_command_line():
    options = [("notifications.slack_webhook_url", SLACK_WEBHOOK), ("sentry.dsn", SENTRY_DSN)]
    builder = ConfigurationBuilder.from_commandline_options(
        CommonServerOptions(options=options, applications=["notifications", "harp_apps.contrib.sentry"])
    )
    settings = builder.build()

    assert settings["notifications"].slack_webhook_url.get_secret_value() == SLACK_WEBHOOK
    assert settings["harp_apps.contrib.sentry"].dsn.get_secret_value() == SENTRY_DSN

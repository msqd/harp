import asyncio

import pytest

from harp.commandline.options.server import CommonServerOptions
from harp.config import ConfigurationBuilder
from harp_apps.dashboard.controllers.system import SystemController

ALL_APPLICATIONS = (
    "http_client",
    "http_cache",
    "proxy",
    "storage",
    "dashboard",
    "janitor",
    "rules",
    "metrics",
    "notifications",
    "acme",
    "harp_apps.contrib.sentry",
)


def _build(tmp_path, applications, extra=""):
    path = tmp_path / "harp.yml"
    path.write_text(f"applications: [{', '.join(applications)}]\n{extra}")
    return ConfigurationBuilder.from_commandline_options(CommonServerOptions(files=(str(path),))).build()


def _get_settings(settings):
    controller = SystemController(storage=None, settings=settings, resolver=None, handle_errors=False)
    return asyncio.run(controller.get_settings())


def test_settings_answer_with_the_cache_on(tmp_path):
    response = _get_settings(_build(tmp_path, ["http_client", "http_cache", "proxy"]))

    assert response.status == 200
    assert response.asdict()["http_cache"]["purge"]["allow"] == ["127.0.0.1/32"]


def test_settings_answer_with_trusted_proxies(tmp_path):
    response = _get_settings(_build(tmp_path, ["proxy"], "proxy:\n  trusted_proxies: [10.0.0.0/8, '::1']\n"))

    assert response.status == 200
    assert response.asdict()["proxy"]["trusted_proxies"] == ["10.0.0.0/8", "::1/128"]


@pytest.mark.parametrize("application", ALL_APPLICATIONS)
def test_default_settings_of_every_app_serialize(tmp_path, application):
    response = _get_settings(_build(tmp_path, [application]))

    assert response.status == 200

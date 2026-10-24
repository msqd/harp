"""The recording cap is a proxy setting, handed to every endpoint controller."""

import pytest

from harp.config import ConfigurationBuilder
from harp_apps.proxy.settings import ProxySettings


def test_recording_cap_defaults_to_one_mebibyte():
    assert ProxySettings().max_recorded_body_size == 1024 * 1024


@pytest.mark.parametrize("value, expected", [(4096, 4096), ("2MiB", 2 * 1024 * 1024), ("64KiB", 64 * 1024)])
def test_recording_cap_accepts_a_byte_count_or_a_size_with_its_unit(value, expected):
    assert ProxySettings(max_recorded_body_size=value).max_recorded_body_size == expected


async def test_recording_cap_reaches_the_endpoint_controllers():
    system = await ConfigurationBuilder(
        {
            "applications": ["http_client", "proxy"],
            "proxy": {
                "max_recorded_body_size": "2MiB",
                "endpoints": [{"name": "api", "port": 8080, "url": "http://example.com/"}],
            },
        },
        use_default_applications=False,
    ).abuild_system(validate_dependencies=False)

    try:
        controller = system.provider.get("proxy.controllers.api_controller")
        assert controller.max_recorded_body_size == 2 * 1024 * 1024
    finally:
        await system.dispose()


def test_request_body_rate_defaults():
    settings = ProxySettings()
    assert settings.min_request_body_rate == 1024
    assert settings.request_body_grace_period == 10.0


async def test_request_body_rate_reaches_the_endpoint_controllers():
    system = await ConfigurationBuilder(
        {
            "applications": ["http_client", "proxy"],
            "proxy": {
                "min_request_body_rate": "2KiB",
                "request_body_grace_period": 5,
                "endpoints": [{"name": "api", "port": 8080, "url": "http://example.com/"}],
            },
        },
        use_default_applications=False,
    ).abuild_system(validate_dependencies=False)

    try:
        controller = system.provider.get("proxy.controllers.api_controller")
        assert (controller.min_request_body_rate, controller.request_body_grace_period) == (2048, 5)
    finally:
        await system.dispose()

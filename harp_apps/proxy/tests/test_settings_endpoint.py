import pytest
from pydantic import ValidationError

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.settings import EndpointSettings
from harp_apps.proxy.settings.endpoint import Endpoint

base_settings = {
    "name": "my-endpoint",
    "port": 8080,
}
remote_settings = {"endpoints": [{"url": "http://example.com/"}]}


custom_controller = {"type": "harp_apps.proxy.tests.test_settings_endpoint.StaticController"}


class StaticController:
    """A custom controller that has no use for a remote."""

    def __init__(self, name=None):
        self.name = name

    async def __call__(self, request):
        return "static"


class TestEndpointSettings:
    def test_old_url_syntax(self):
        obj = EndpointSettings(**base_settings, url="http://my-endpoint:8080")
        assert asdict(obj) == {
            **base_settings,
            "remote": {"endpoints": [{"url": "http://my-endpoint:8080/"}]},
        }


class TestEndpointSettingsWithCustomController(BaseConfigurableTest):
    type = EndpointSettings
    initial = {**base_settings, "controller": custom_controller}
    expected = {**initial}
    expected_verbose = {
        **expected,
        "description": None,
        "remote": None,
        "controller": custom_controller,
    }


class TestEndpointSettingsWithRemote(BaseConfigurableTest):
    type = EndpointSettings
    initial = {
        **base_settings,
        "remote": remote_settings,
    }
    expected = {**initial}
    expected_verbose = {
        **expected,
        "description": None,
        "remote": {
            "break_on": ["network_error", "unhandled_exception"],
            "check_after": 10.0,
            "endpoints": [
                {
                    "liveness": {"type": "inherit"},
                    "pools": ["default"],
                    "url": "http://example.com/",
                }
            ],
            "min_pool_size": 1,
            "probe": None,
            "liveness": {"type": "inherit"},
        },
        "controller": {
            "type": "harp_apps.proxy.controllers.HttpProxyController",
            "dispatcher": {"type": "IAsyncEventDispatcher"},
        },
    }


class TestEndpointStatefulWithCustomController(BaseConfigurableTest):
    type = Endpoint
    initial = {
        "settings": TestEndpointSettingsWithCustomController.initial,
    }
    expected = {
        "settings": {
            **base_settings,
            "description": None,
        },
    }
    expected_verbose = {
        **expected,
        "remote": None,
    }

    def test_repr(self):
        obj = self.create()
        assert repr(obj) == "Endpoint(remote=None)"


class TestEndpointStatefulWithRemote(BaseConfigurableTest):
    type = Endpoint
    initial = {
        "settings": TestEndpointSettingsWithRemote.initial,
    }
    expected = {
        "remote": {
            "current_pool": ["http://example.com/"],
            "endpoints": [
                {
                    "settings": {
                        "liveness": {"type": "inherit"},
                        "url": "http://example.com/",
                        "pools": ["default"],
                    },
                }
            ],
            "settings": {
                "break_on": ["network_error", "unhandled_exception"],
                "check_after": 10.0,
                "min_pool_size": 1,
            },
        },
        "settings": {
            **base_settings,
            "description": None,
        },
    }

    expected_verbose = {
        "remote": {
            "current_pool": ["http://example.com/"],
            "current_pool_name": "default",
            "endpoints": [
                {
                    "failure_reasons": None,
                    "settings": {"liveness": {"type": "inherit"}, "pools": ["default"], "url": "http://example.com/"},
                    "status": 0,
                }
            ],
            "probe": None,
            "settings": {"break_on": ["network_error", "unhandled_exception"], "check_after": 10.0, "min_pool_size": 1},
        },
        "settings": expected["settings"],
    }


class TestEndpointSettingsValidation:
    def test_null_controller_selects_default(self):
        settings = EndpointSettings(**base_settings, url="http://example.com/", controller=None)
        assert settings.controller == EndpointSettings(**base_settings, url="http://example.com/").controller

    def test_default_controller_without_url_nor_remote_is_refused(self):
        with pytest.raises(ValidationError, match="my-endpoint"):
            EndpointSettings(**base_settings)

    def test_null_controller_without_url_nor_remote_is_refused(self):
        with pytest.raises(ValidationError, match="my-endpoint"):
            EndpointSettings(**base_settings, controller=None)

    def test_explicit_default_controller_without_url_nor_remote_is_refused(self):
        with pytest.raises(ValidationError, match="my-endpoint"):
            EndpointSettings(**base_settings, controller="harp_apps.proxy.controllers.HttpProxyController")

    def test_custom_controller_without_url_nor_remote_is_accepted(self):
        assert EndpointSettings(**base_settings, controller=custom_controller).remote is None


async def test_custom_controller_without_remote_binds():
    builder = ConfigurationBuilder(
        {"applications": ["http_client", "proxy"]},
        use_default_applications=False,
    )
    builder.add_values({"proxy": {"endpoints": [{**base_settings, "controller": custom_controller}]}})

    system = await builder.abuild_system()
    await system.dispose()

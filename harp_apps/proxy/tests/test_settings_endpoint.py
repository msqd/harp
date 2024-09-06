from harp.config.asdict import asdict
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.settings import EndpointSettings
from harp_apps.proxy.settings.endpoint import Endpoint

base_settings = {
    "name": "my-endpoint",
    "port": 8080,
}
remote_settings = {"endpoints": [{"url": "http://example.com/"}]}


class TestEndpointSettings(BaseConfigurableTest):
    type = EndpointSettings
    initial = {**base_settings}
    expected = {**initial}
    expected_verbose = {**expected, "description": None, "remote": None}

    def test_old_url_syntax(self):
        obj = self.create(url="http://my-endpoint:8080")
        assert asdict(obj) == {
            **self.expected,
            "remote": {"endpoints": [{"url": "http://my-endpoint:8080/"}]},
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
    }


class TestEndpointStateful(BaseConfigurableTest):
    type = Endpoint
    initial = {
        "settings": TestEndpointSettings.initial,
    }
    expected = {
        "settings": {
            **TestEndpointSettings.expected,
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
        "settings": {**TestEndpointSettings.expected, "description": None},
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

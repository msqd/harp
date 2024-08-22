from harp.config import asdict
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
                {"failure_threshold": 1, "pools": ["default"], "success_threshold": 1, "url": "http://example.com/"}
            ],
            "min_pool_size": 1,
            "probe": None,
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
                        "url": "http://example.com/",
                        "failure_threshold": 1,
                        "pools": ["default"],
                        "success_threshold": 1,
                    }
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
                    "status": 0,
                    "failure_reasons": None,
                    "failure_score": 0,
                    "success_score": 0,
                    "settings": {
                        "failure_threshold": 1,
                        "pools": ["default"],
                        "success_threshold": 1,
                        "url": "http://example.com/",
                    },
                }
            ],
            "probe": None,
            "settings": {
                "break_on": ["network_error", "unhandled_exception"],
                "check_after": 10.0,
                "min_pool_size": 1,
            },
        },
        "settings": expected["settings"],
    }

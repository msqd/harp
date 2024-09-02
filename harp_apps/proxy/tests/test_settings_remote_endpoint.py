import pytest
from pydantic import ValidationError

from harp.config.asdict import asdict
from harp.utils.collections import all_combinations
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.constants import AVAILABLE_POOLS
from harp_apps.proxy.settings.remote import RemoteEndpointSettings
from harp_apps.proxy.settings.remote.endpoint import RemoteEndpoint


class TestRemoteEndpointSettings(BaseConfigurableTest):
    type = RemoteEndpointSettings
    initial = {"url": "http://example.com"}
    expected = {"url": "http://example.com/"}
    expected_verbose = {
        "url": "http://example.com/",
        "pools": ["default"],
        "failure_threshold": 1,
        "success_threshold": 1,
    }

    def test_defaults2(self):
        settings = RemoteEndpointSettings(url="http://example.com")

        assert settings.model_dump(mode="json") == {
            "url": "http://example.com/",
            "pools": ["default"],
            "failure_threshold": 1,
            "success_threshold": 1,
        }

    @pytest.mark.parametrize("pools", all_combinations(AVAILABLE_POOLS))
    def test_valid_pools(self, pools):
        obj = self.create(pools=pools)
        assert asdict(obj) == {**self.expected, "pools": list(sorted(pools))}

    def test_invalid_pool(self):
        invalid_data = {"url": "http://example.com", "pools": ["invalid"]}
        with pytest.raises(ValueError):
            RemoteEndpointSettings(**invalid_data)

        with pytest.raises(ValidationError) as exc_info:
            RemoteEndpointSettings.model_validate(invalid_data)

        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("pools",)
        assert errors[0]["msg"] == "Value error, Invalid pool names: invalid."

    def test_valid_thresholds(self):
        valid_data = {
            "url": "http://example.com",
            "failure_threshold": 3,
            "success_threshold": 5,
        }
        settings = RemoteEndpointSettings(**valid_data)
        assert settings.failure_threshold == 3
        assert settings.success_threshold == 5

    def test_asdict(self):
        endpoint = self.create(url="http://example.com")
        expected = {
            "url": "http://example.com/",
        }
        assert asdict(endpoint) == expected

        # idempotence
        endpoint = self.create(**asdict(endpoint))
        assert asdict(endpoint) == expected

    def test_asdict_with_nondefault_thresholds(self):
        endpoint = self.create(url="http://example.com", success_threshold=2, failure_threshold=4)
        expected = {
            "url": "http://example.com/",
            "success_threshold": 2,
            "failure_threshold": 4,
        }
        assert asdict(endpoint) == expected

        # idempotence
        endpoint = RemoteEndpointSettings(**asdict(endpoint))
        assert asdict(endpoint) == expected


class TestRemoteEndpointStateful(BaseConfigurableTest):
    type = RemoteEndpoint
    initial = {"settings": TestRemoteEndpointSettings.initial}
    expected = {
        "settings": {
            "failure_threshold": 1,
            "pools": ["default"],
            "success_threshold": 1,
            "url": "http://example.com/",
        }
    }
    expected_verbose = {
        "settings": TestRemoteEndpointSettings.expected_verbose,
        "failure_reasons": None,
        "failure_score": 0,
        "status": 0,
        "success_score": 0,
    }

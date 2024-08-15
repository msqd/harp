from itertools import chain, combinations

import pytest
from pydantic import ValidationError

from harp.config import asdict
from harp_apps.proxy.constants import AVAILABLE_POOLS
from harp_apps.proxy.settings.remote import RemoteEndpointSettings


def all_combinations(iterable):
    return set(chain(*(combinations(iterable, n + 1) for n in range(len(iterable)))))


def test_defaults():
    settings = RemoteEndpointSettings(url="http://example.com")

    assert settings.model_dump(mode="json") == {
        "url": "http://example.com/",
        "pools": ["default"],
        "failure_threshold": 1,
        "success_threshold": 1,
    }


@pytest.mark.parametrize("pools", all_combinations(AVAILABLE_POOLS))
def test_valid_pools(pools):
    valid_data = {"url": "http://example.com", "pools": pools}
    assert asdict(RemoteEndpointSettings(**valid_data)) == {"url": "http://example.com/", "pools": list(sorted(pools))}


def test_invalid_pool():
    invalid_data = {"url": "http://example.com", "pools": ["invalid"]}
    with pytest.raises(ValueError):
        RemoteEndpointSettings(**invalid_data)

    with pytest.raises(ValidationError) as exc_info:
        RemoteEndpointSettings.model_validate(invalid_data)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("pools",)
    assert errors[0]["msg"] == "Value error, Invalid pool names: invalid."


def test_valid_thresholds():
    valid_data = {"url": "http://example.com", "failure_threshold": 3, "success_threshold": 5}
    settings = RemoteEndpointSettings(**valid_data)
    assert settings.failure_threshold == 3
    assert settings.success_threshold == 5

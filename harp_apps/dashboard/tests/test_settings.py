import pytest

from harp.errors import ConfigurationError

from ..settings import DashboardAuthSetting


def test_no_auth():
    assert DashboardAuthSetting() is None
    assert DashboardAuthSetting(type="") is None
    assert DashboardAuthSetting(type=None) is None


def test_invalid_auth():
    with pytest.raises(ConfigurationError):
        DashboardAuthSetting(type=None, value="no chance")

    with pytest.raises(ConfigurationError):
        DashboardAuthSetting(type="invalid")


def test_basic_auth():
    assert DashboardAuthSetting(
        type="basic",
        algorithm="plain",
        users={"foo": "bar"},
    ).to_dict() == {
        "type": "basic",
        "algorithm": "plain",
        "users": {"foo": "bar"},
    }

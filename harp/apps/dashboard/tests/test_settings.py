import pytest

from harp.apps.dashboard.settings import DashboardAuthSetting, DashboardSettings
from harp.config.settings import DisabledSettings
from harp.errors import ProxyConfigurationError


def test_no_auth():
    assert DashboardAuthSetting() is None
    assert DashboardAuthSetting(type="") is None
    assert DashboardAuthSetting(type=None) is None


def test_invalid_auth():
    with pytest.raises(ProxyConfigurationError):
        DashboardAuthSetting(type=None, value="no chance")

    with pytest.raises(ProxyConfigurationError):
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


def test_disabled():
    assert isinstance(DashboardSettings(enabled=False), DisabledSettings)
    assert isinstance(DashboardSettings(), DashboardSettings)

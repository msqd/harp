import pytest

from harp.applications.dashboard.settings import DashboardAuthSettings, DashboardSettings
from harp.core.settings.common import DisabledSettings
from harp.errors import ProxyConfigurationError


def test_no_auth():
    assert DashboardAuthSettings() is None
    assert DashboardAuthSettings(type="") is None
    assert DashboardAuthSettings(type=None) is None


def test_invalid_auth():
    with pytest.raises(ProxyConfigurationError):
        DashboardAuthSettings(type=None, value="no chance")

    with pytest.raises(ProxyConfigurationError):
        DashboardAuthSettings(type="invalid")


def test_basic_auth():
    assert DashboardAuthSettings(
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

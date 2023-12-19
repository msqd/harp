import pytest

from harp.applications.dashboard.settings import DashboardAuthSettings, DashboardSettings, DisabledSettings
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


@pytest.mark.skip(reason="todo")
def test_basic_auth():
    DashboardAuthSettings(type="basic", passwd={"foo": "bar"})


def test_disabled():
    assert isinstance(DashboardSettings(enabled=False), DisabledSettings)
    assert isinstance(DashboardSettings(), DashboardSettings)

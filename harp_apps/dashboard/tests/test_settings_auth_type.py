import pytest
from pydantic import ValidationError

from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings


def test_auth_is_unset_by_default():
    assert DashboardSettings().auth is None


def test_there_is_no_open_mode():
    with pytest.raises(ValidationError, match="no open mode"):
        DashboardSettings(auth={"type": "none"})


def test_auth_without_type_is_still_basic():
    assert isinstance(DashboardSettings(auth={"users": {"alice": "pw"}}).auth, BasicAuthSettings)


def test_basic_type_survives_a_defaults_free_dump():
    dumped = DashboardSettings(auth={"users": {"alice": "pw"}}).model_dump(exclude_defaults=True, exclude_unset=True)

    assert dumped["auth"]["type"] == "basic"
    assert isinstance(DashboardSettings(**dumped).auth, BasicAuthSettings)

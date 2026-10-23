import pytest
from pydantic import ValidationError

from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings, NoAuthSettings


def test_auth_is_unset_by_default():
    assert DashboardSettings().auth is None


def test_none_type_opts_out():
    assert isinstance(DashboardSettings(auth={"type": "none"}).auth, NoAuthSettings)


def test_none_type_survives_a_defaults_free_dump():
    dumped = DashboardSettings(auth={"type": "none"}).model_dump(exclude_defaults=True, exclude_unset=True)

    assert dumped["auth"] == {"type": "none"}
    assert isinstance(DashboardSettings(**dumped).auth, NoAuthSettings)


def test_auth_without_type_is_still_basic():
    assert isinstance(DashboardSettings(auth={"users": {"alice": "pw"}}).auth, BasicAuthSettings)


def test_none_type_takes_no_users():
    with pytest.raises(ValidationError):
        DashboardSettings(auth={"type": "none", "users": {"alice": "pw"}})

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp_apps.auth.settings import AuthSettings


def test_defaults():
    assert asdict(AuthSettings(), verbose=True) == {
        "enabled": True,
        "session_idle_hours": 12,
        "session_max_hours": 168,
        "setup_link_hours": 72,
    }


def test_auth_is_loaded_by_default_before_the_dashboard_that_needs_it():
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.build()

    names = list(builder.applications)
    assert names.index("storage") < names.index("auth") < names.index("dashboard")


def test_disabled_auth_is_not_loaded():
    builder = ConfigurationBuilder(use_default_applications=True)
    builder.add_values({"auth": {"enabled": False}})
    builder.build()

    assert "auth" not in builder.applications

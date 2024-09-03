from tempfile import NamedTemporaryFile

from harp.config.asdict import asdict
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings


def test_defaults():
    assert asdict(DashboardSettings()) == {}

    assert asdict(DashboardSettings(), verbose=True) == {
        "auth": None,
        "devserver": {"enabled": True, "port": None},
        "enable_ui": True,
        "port": 4080,
        "public_url": None,
    }


def test_basic_auth_defaults():
    assert asdict(BasicAuthSettings()) == {"type": "basic"}
    assert asdict(BasicAuthSettings(), verbose=True) == {
        "algorithm": "pbkdf2_sha256",
        "type": "basic",
        "users": {},
    }


def test_basic_auth_userlist():
    settings = BasicAuthSettings.from_dict({"users": {"john": "foo", "jane": "bar"}})
    assert asdict(settings) == {
        "type": "basic",
        "users": {"jane": {"password": "bar"}, "john": {"password": "foo"}},
    }

    assert asdict(settings, verbose=True) == {
        "algorithm": "pbkdf2_sha256",
        "type": "basic",
        "users": {"jane": {"password": "bar"}, "john": {"password": "foo"}},
    }


def test_basic_auth_userlist_fromfile():
    with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
        f.write("john: foo\njane: bar\n")
        f.flush()

        assert asdict(BasicAuthSettings.from_dict({"users": {"fromFile": f.name}, "algorithm": "plain"})) == {
            "algorithm": "plaintext",
            "type": "basic",
            "users": {"jane": {"password": "bar"}, "john": {"password": "foo"}},
        }


def test_no_devserver():
    settings = DashboardSettings()
    assert settings.devserver.enabled is True


def test_devserver_disable():
    settings = DashboardSettings.from_dict({"devserver": {"enabled": False}})
    assert settings.devserver.enabled is False

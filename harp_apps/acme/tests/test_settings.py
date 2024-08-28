from harp.config.asdict import asdict

from ..settings import AcmeSettings


def test_default_settings():
    settings = AcmeSettings()
    assert asdict(settings) == {"owner": "Joe"}


def test_custom_settings():
    settings = AcmeSettings(owner="Alice")
    assert asdict(settings) == {"owner": "Alice"}

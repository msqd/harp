from harp.config import DisabledSettings, asdict


def test_disabled_settings():
    setting = DisabledSettings()
    assert asdict(setting) == {"enabled": False}
    assert repr(setting) == "disabled"

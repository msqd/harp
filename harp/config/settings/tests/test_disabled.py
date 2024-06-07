import pytest

from harp.config import DisabledSettings


def test_disabled_settings_cannot_be_enabled():
    disabled_settings = DisabledSettings()
    assert disabled_settings.enabled is False
    with pytest.raises(ValueError):
        disabled_settings.enabled = True

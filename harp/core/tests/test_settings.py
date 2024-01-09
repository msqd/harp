import os
from tempfile import NamedTemporaryFile

from harp.config.settings import DisabledSettings, FromFileSetting


def test_from_file_setting_not_existing():
    filename = "/this/is/very/unlikely/to/exist"
    setting = FromFileSetting(from_file=filename)
    assert setting.to_dict() == {"from_file": filename}
    assert not setting.exists()


def test_from_file_setting_existing():
    try:
        with NamedTemporaryFile("w+", delete=False) as tmp_file:
            tmp_file.write("test")
            setting = FromFileSetting(from_file=tmp_file.name)
            assert setting.to_dict() == {"from_file": tmp_file.name}
            assert setting.exists()

        with setting.open() as f:
            assert f.read() == "test"
    finally:
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)


def test_disabled_settings():
    setting = DisabledSettings()
    assert setting.to_dict() == {"enabled": False}
    assert repr(setting) == "disabled"

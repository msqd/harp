from tempfile import NamedTemporaryFile
from unittest.mock import Mock

from harp_apps.rules.models.scripts import Script


def test_script_from_sources():
    script = Script("print('Hello, World!')")
    assert script.source == "print('Hello, World!')"

    print_mock = Mock()
    script({"print": print_mock})

    assert print_mock.called
    assert print_mock.call_count == 1


def test_script_from_file():
    with NamedTemporaryFile("w", delete=False) as f:
        f.write("print('Hello, World!')")
        f.flush()

    script = Script.from_file(f.name)
    assert script.source == "print('Hello, World!')"

    print_mock = Mock()
    script({"print": print_mock})

    assert print_mock.called
    assert print_mock.call_count == 1

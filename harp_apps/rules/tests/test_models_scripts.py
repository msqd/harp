import builtins
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


def test_script_globals_do_not_leak_between_scripts():
    Script("global leaked\nleaked = 42")({})
    probe = {"found": None}
    Script("found = 'leaked' in globals()")(probe)

    assert probe["found"] is False


def test_script_builtins_changes_do_not_leak():
    Script("__builtins__['harp_leak'] = 1")({})

    assert not hasattr(builtins, "harp_leak")
    probe = {"found": None}
    Script("found = 'harp_leak' in dir(__builtins__) or 'harp_leak' in __builtins__")(probe)
    assert probe["found"] is False


def test_script_function_sees_context():
    context = {"request": "the request", "seen": None}
    Script("def get():\n    return request\nseen = get()")(context)

    assert context["seen"] == "the request"


def test_script_assignment_updates_context():
    context = {"response": None}
    Script("response = 'replaced'")(context)

    assert context["response"] == "replaced"

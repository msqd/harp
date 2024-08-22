from harp.services.models import _resolve
from harp.services.references import SettingReference


def test_basic_cfgref():
    ref = SettingReference("foo.bar")
    assert ref.resolve({"foo": {"bar": "baz"}}) == "baz"


def test_equality_cfgref():
    ref = SettingReference("foo.bar == 'baz'")
    assert ref.resolve({"foo": {"bar": "baz"}}) is True
    assert ref.resolve({"foo": {"bar": "boo"}}) is None


def test_resolve_dict_with_references():
    arguments = {
        "foobar": SettingReference("foo.bar"),
    }
    assert _resolve(arguments, {"foo": {"bar": "baz"}}) == {"foobar": "baz"}


def test_resolve_dict_with_deep_references():
    arguments = {
        "foo": {"bar": SettingReference("foo.bar")},
    }
    assert _resolve(arguments, {"foo": {"bar": "baz"}}) == {"foo": {"bar": "baz"}}

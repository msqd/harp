import pytest

from harp.services.models import _resolve
from harp.services.references import LazySettingReference


def test_basic_cfgref():
    ref = LazySettingReference("foo.bar")
    assert ref.resolve({"foo": {"bar": "baz"}}) == "baz"


def test_equality_cfgref():
    ref = LazySettingReference("foo.bar == 'baz'")
    assert ref.resolve({"foo": {"bar": "baz"}}) is True
    assert ref.resolve({"foo": {"bar": "boo"}}) is None


def test_cfgref_operand_must_be_a_literal():
    # The right-hand operand is parsed as a Python literal, never executed as code.
    ref = LazySettingReference("foo.bar == __import__('os').getcwd()")
    with pytest.raises(ValueError):
        ref.resolve({"foo": {"bar": "baz"}})


def test_resolve_dict_with_references():
    arguments = {
        "foobar": LazySettingReference("foo.bar"),
    }
    assert _resolve(arguments, {"foo": {"bar": "baz"}}) == {"foobar": "baz"}


def test_resolve_dict_with_deep_references():
    arguments = {
        "foo": {"bar": LazySettingReference("foo.bar")},
    }
    assert _resolve(arguments, {"foo": {"bar": "baz"}}) == {"foo": {"bar": "baz"}}

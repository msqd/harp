import sys
from types import ModuleType

import pytest

from harp import _native
from harp._native import NativeUnavailableError, active, select


def python_impl():
    return "python"


def native_impl():
    return "native"


@pytest.fixture(autouse=True)
def components(monkeypatch):
    monkeypatch.delenv("HARP_NATIVE", raising=False)
    monkeypatch.setattr(_native, "COMPONENTS", frozenset({"blob_id", "other"}))


@pytest.fixture
def core(monkeypatch):
    module = ModuleType("harp._native._core")
    module.blob_id = native_impl
    monkeypatch.setitem(sys.modules, "harp._native._core", module)
    return module


@pytest.mark.parametrize("value", [None, "", "none"])
def test_python_by_default(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("HARP_NATIVE", value)
    assert select("blob_id", python_impl) is python_impl
    assert active() == {"blob_id": "python", "other": "python"}


def test_unknown_component_in_select():
    with pytest.raises(ValueError, match="nope"):
        select("nope", python_impl)


def test_unknown_component_in_env(monkeypatch):
    monkeypatch.setenv("HARP_NATIVE", "blob_id,nope")
    with pytest.raises(ValueError, match="nope"):
        select("blob_id", python_impl)


@pytest.mark.parametrize("value", ["all", "blob_id"])
def test_missing_extension_fails_hard(monkeypatch, value):
    monkeypatch.setenv("HARP_NATIVE", value)
    monkeypatch.setitem(sys.modules, "harp._native._core", None)
    with pytest.raises(NativeUnavailableError):
        select("blob_id", python_impl)


def test_listed_component_without_native_impl_fails_hard(monkeypatch, core):
    monkeypatch.setenv("HARP_NATIVE", "other")
    with pytest.raises(NativeUnavailableError, match="other"):
        select("other", python_impl)


def test_explicit_list_selects_native_only_for_listed(monkeypatch, core):
    monkeypatch.setenv("HARP_NATIVE", "blob_id")
    assert select("blob_id", python_impl) is native_impl
    assert select("other", python_impl) is python_impl
    assert active() == {"blob_id": "native", "other": "python"}


def test_all_selects_native_where_available(monkeypatch, core):
    monkeypatch.setenv("HARP_NATIVE", "all")
    assert select("blob_id", python_impl) is native_impl
    assert select("other", python_impl) is python_impl
    assert active() == {"blob_id": "native", "other": "python"}

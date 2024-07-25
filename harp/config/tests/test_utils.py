from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch

import pytest

from harp.config import Application
from harp.config.utils import get_application, resolve_application_name

# fake module for foo.bar
foobar_module = ModuleType("foo.bar")
foobar_module.__spec__ = ModuleSpec(name="foo.bar", loader=None)

# fake module for foo.bar.__app__
foobar_app_module = ModuleType("foo.bar.__app__")
foobar_app_module.application = Application()
foobar_app_module.__spec__ = ModuleSpec(name="foo.bar.__app__", loader=None)

# fake module for acme.storage
acme_storage_module = ModuleType("acme.storage")
acme_storage_module.__spec__ = ModuleSpec(name="acme.storage", loader=None)

# fake module for acme.storage.__app__
acme_storage_app_module = ModuleType("acme.storage.__app__")
acme_storage_app_module.application = Application()
acme_storage_app_module.__spec__ = ModuleSpec(name="acme.storage.__app__", loader=None)


def test_resolve_application_name():
    assert resolve_application_name("storage") == "harp_apps.storage"
    assert resolve_application_name("harp_apps.storage") == "harp_apps.storage"

    with pytest.raises(ModuleNotFoundError):
        resolve_application_name("foo.bar")

    with patch.dict(
        "sys.modules",
        {
            "foo.bar": foobar_module,
        },
    ):
        assert resolve_application_name("foo.bar") == "foo.bar"

    # check that our resolver do not resolve if the module is not available anymore (to test one issue we add because
    # of an added lru_cache)
    with pytest.raises(ModuleNotFoundError):
        resolve_application_name("foo.bar")


def test_get_application():
    storage_app = get_application("storage")
    assert get_application("harp_apps.storage") is storage_app
    assert get_application("storage") is storage_app


def test_get_overriden_application():
    with patch.dict(
        "sys.modules",
        {
            "acme.storage": acme_storage_module,
            "acme.storage.__app__": acme_storage_app_module,
        },
    ):
        storage_app = get_application("acme.storage")
        assert get_application("acme.storage") is storage_app
        assert get_application("storage") is not storage_app

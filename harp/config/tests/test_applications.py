from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch

import pytest

from harp.config import Application, ApplicationsRegistry

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


class TestApplicationsRegistry:
    @pytest.fixture()
    def registry(self):
        return ApplicationsRegistry()

    def test_add_remove(self, registry):
        assert len(registry) == 0
        assert "storage" not in registry

        registry.add("storage")
        assert len(registry) == 1
        assert "storage" in registry

        assert registry.resolve_name("storage") == "harp_apps.storage"
        assert registry.aslist() == ["harp_apps.storage"]

        registry.add("harp_apps.rules")
        assert len(registry) == 2
        assert "rules" in registry

        assert registry.resolve_name("rules") == "harp_apps.rules"
        assert registry.aslist() == ["harp_apps.storage", "harp_apps.rules"]

        registry.add("acme")
        assert len(registry) == 3
        assert "acme" in registry

        assert registry.resolve_name("acme") == "harp_apps.acme"
        assert registry.aslist() == [
            "harp_apps.storage",
            "harp_apps.rules",
            "harp_apps.acme",
        ]

        registry.remove("rules")
        assert len(registry) == 2
        assert "rules" not in registry

        assert registry.aslist() == ["harp_apps.storage", "harp_apps.acme"]

    def test_resolve_name(self, registry):
        assert registry.resolve_name("storage") == "harp_apps.storage"
        assert registry.resolve_name("harp_apps.storage") == "harp_apps.storage"

        with pytest.raises(ModuleNotFoundError):
            registry.resolve_name("foo.bar")

        with patch.dict(
            "sys.modules",
            {
                "foo.bar": foobar_module,
            },
        ):
            assert registry.resolve_name("foo.bar") == "foo.bar"

        # check that our resolver do not resolve if the module is not available anymore (to test one issue we add because
        # of an added lru_cache)
        with pytest.raises(ModuleNotFoundError):
            registry.resolve_name("foo.bar")

    def test_get_application(self, registry):
        storage_app = registry.get_application("storage")
        assert registry.get_application("harp_apps.storage") is storage_app
        assert registry.get_application("storage") is storage_app

    def test_get_overriden_application(self, registry):
        with patch.dict(
            "sys.modules",
            {
                "acme.storage": acme_storage_module,
                "acme.storage.__app__": acme_storage_app_module,
            },
        ):
            storage_app = registry.get_application("acme.storage")
            assert registry.get_application("acme.storage") is storage_app
            assert registry.get_application("storage") is not storage_app

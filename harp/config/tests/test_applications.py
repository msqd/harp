import pytest

from harp.config import ApplicationsRegistry


class TestApplicationsRegistry:
    def test_add_remove(self):
        registry = ApplicationsRegistry()

        assert len(registry) == 0
        assert "storage" not in registry

        registry.add("storage")
        assert len(registry) == 1
        assert "storage" in registry

        assert registry.get_full_name("storage") == "harp_apps.storage"
        assert registry.aslist() == ["harp_apps.storage"]

        registry.add("harp_apps.rules")
        assert len(registry) == 2
        assert "rules" in registry

        assert registry.get_full_name("rules") == "harp_apps.rules"
        assert registry.aslist() == ["harp_apps.storage", "harp_apps.rules"]

        registry.add("acme")
        assert len(registry) == 3
        assert "acme" in registry

        assert registry.get_full_name("acme") == "harp_apps.acme"
        assert registry.aslist() == ["harp_apps.storage", "harp_apps.rules", "harp_apps.acme"]

        registry.remove("rules")
        assert len(registry) == 2
        assert "rules" not in registry

        with pytest.raises(KeyError):
            registry.get_full_name("rules")

        assert registry.aslist() == ["harp_apps.storage", "harp_apps.acme"]

"""
Integration tests for SystemBuilder dependency resolution.

These tests verify that SystemBuilder.abuild() correctly validates and resolves
application dependencies during system startup, failing fast when dependencies
are invalid or missing.
"""

from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch

import pytest

from harp.config import Application, ApplicationsRegistry
from harp.config.builders.system import SystemBuilder
from harp.errors import CircularDependencyError, MissingDependencyError
from harp.typing import GlobalSettings


class TestSystemBuilderDependencyIntegration:
    """Integration tests for dependency resolution during system build."""

    @pytest.mark.asyncio
    async def test_valid_dependencies_build_successfully(self):
        """
        Test that SystemBuilder successfully builds when all dependencies are valid.

        Scenario: storage app has no dependencies, proxy depends on storage.
        Expected: System builds successfully with apps in correct order.
        """
        # Create fake module hierarchy for storage
        storage_module = ModuleType("test.storage")
        storage_module.__spec__ = ModuleSpec(name="test.storage", loader=None)
        storage_app_module = ModuleType("test.storage.__app__")
        storage_app_module.__spec__ = ModuleSpec(name="test.storage.__app__", loader=None)
        storage_app = Application()
        storage_app_module.application = storage_app

        # Create fake module hierarchy for proxy
        proxy_module = ModuleType("test.proxy")
        proxy_module.__spec__ = ModuleSpec(name="test.proxy", loader=None)
        proxy_app_module = ModuleType("test.proxy.__app__")
        proxy_app_module.__spec__ = ModuleSpec(name="test.proxy.__app__", loader=None)
        proxy_app = Application(dependencies=["storage"])
        proxy_app_module.application = proxy_app

        with patch.dict(
            "sys.modules",
            {
                "test.storage": storage_module,
                "test.storage.__app__": storage_app_module,
                "test.proxy": proxy_module,
                "test.proxy.__app__": proxy_app_module,
            },
        ):
            # Create registry with dependencies
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.storage")
            registry.add("test.proxy")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should succeed
            builder = SystemBuilder(registry, config)
            system = await builder.abuild()

            # Verify system was built
            assert system is not None
            assert system.config is config
            assert system.dispatcher is not None
            assert system.provider is not None
            assert system.asgi_app is not None

            # Cleanup
            await system.dispose()

    @pytest.mark.asyncio
    async def test_missing_dependency_fails_at_build(self):
        """
        Test that SystemBuilder.abuild() raises MissingDependencyError when dependency is missing.

        Scenario: proxy depends on storage, but storage is not in registry.
        Expected: MissingDependencyError raised during build.
        """
        # Create fake module hierarchy for proxy only
        proxy_module = ModuleType("test.proxy")
        proxy_module.__spec__ = ModuleSpec(name="test.proxy", loader=None)
        proxy_app_module = ModuleType("test.proxy.__app__")
        proxy_app_module.__spec__ = ModuleSpec(name="test.proxy.__app__", loader=None)
        proxy_app = Application(dependencies=["storage"])
        proxy_app_module.application = proxy_app

        with patch.dict(
            "sys.modules",
            {
                "test.proxy": proxy_module,
                "test.proxy.__app__": proxy_app_module,
            },
        ):
            # Create registry WITHOUT storage
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.proxy")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should fail fast
            builder = SystemBuilder(registry, config)
            with pytest.raises(MissingDependencyError, match="proxy.*requires.*storage"):
                await builder.abuild()

    @pytest.mark.asyncio
    async def test_circular_dependency_fails_at_build(self):
        """
        Test that SystemBuilder.abuild() raises CircularDependencyError for circular deps.

        Scenario: app_a depends on app_b, app_b depends on app_a (2-node cycle).
        Expected: CircularDependencyError raised during build.
        """
        # Create fake module hierarchy for app_a
        app_a_module = ModuleType("test.app_a")
        app_a_module.__spec__ = ModuleSpec(name="test.app_a", loader=None)
        app_a_app_module = ModuleType("test.app_a.__app__")
        app_a_app_module.__spec__ = ModuleSpec(name="test.app_a.__app__", loader=None)
        app_a = Application(dependencies=["app_b"])
        app_a_app_module.application = app_a

        # Create fake module hierarchy for app_b
        app_b_module = ModuleType("test.app_b")
        app_b_module.__spec__ = ModuleSpec(name="test.app_b", loader=None)
        app_b_app_module = ModuleType("test.app_b.__app__")
        app_b_app_module.__spec__ = ModuleSpec(name="test.app_b.__app__", loader=None)
        app_b = Application(dependencies=["app_a"])
        app_b_app_module.application = app_b

        with patch.dict(
            "sys.modules",
            {
                "test.app_a": app_a_module,
                "test.app_a.__app__": app_a_app_module,
                "test.app_b": app_b_module,
                "test.app_b.__app__": app_b_app_module,
            },
        ):
            # Create registry with circular dependencies
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.app_a")
            registry.add("test.app_b")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should fail fast
            builder = SystemBuilder(registry, config)
            with pytest.raises(CircularDependencyError, match="Circular dependency detected"):
                await builder.abuild()

    @pytest.mark.asyncio
    async def test_three_node_circular_dependency_fails_at_build(self):
        """
        Test that SystemBuilder.abuild() detects 3-node circular dependencies.

        Scenario: app_a -> app_b -> app_c -> app_a (3-node cycle).
        Expected: CircularDependencyError raised during build.
        """
        # Create fake modules for 3-node cycle
        app_a_module = ModuleType("test.app_a")
        app_a_module.__spec__ = ModuleSpec(name="test.app_a", loader=None)
        app_a_app_module = ModuleType("test.app_a.__app__")
        app_a_app_module.__spec__ = ModuleSpec(name="test.app_a.__app__", loader=None)
        app_a = Application(dependencies=["app_b"])
        app_a_app_module.application = app_a

        app_b_module = ModuleType("test.app_b")
        app_b_module.__spec__ = ModuleSpec(name="test.app_b", loader=None)
        app_b_app_module = ModuleType("test.app_b.__app__")
        app_b_app_module.__spec__ = ModuleSpec(name="test.app_b.__app__", loader=None)
        app_b = Application(dependencies=["app_c"])
        app_b_app_module.application = app_b

        app_c_module = ModuleType("test.app_c")
        app_c_module.__spec__ = ModuleSpec(name="test.app_c", loader=None)
        app_c_app_module = ModuleType("test.app_c.__app__")
        app_c_app_module.__spec__ = ModuleSpec(name="test.app_c.__app__", loader=None)
        app_c = Application(dependencies=["app_a"])
        app_c_app_module.application = app_c

        with patch.dict(
            "sys.modules",
            {
                "test.app_a": app_a_module,
                "test.app_a.__app__": app_a_app_module,
                "test.app_b": app_b_module,
                "test.app_b.__app__": app_b_app_module,
                "test.app_c": app_c_module,
                "test.app_c.__app__": app_c_app_module,
            },
        ):
            # Create registry with 3-node circular dependency
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.app_a")
            registry.add("test.app_b")
            registry.add("test.app_c")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should fail fast
            builder = SystemBuilder(registry, config)
            with pytest.raises(CircularDependencyError):
                await builder.abuild()

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_dependencies(self):
        """
        Test that existing apps without dependencies continue to work.

        Scenario: Multiple apps with no declared dependencies.
        Expected: System builds successfully, no changes needed to existing code.
        """
        # Create fake modules without dependencies
        app_1_module = ModuleType("test.app_1")
        app_1_module.__spec__ = ModuleSpec(name="test.app_1", loader=None)
        app_1_app_module = ModuleType("test.app_1.__app__")
        app_1_app_module.__spec__ = ModuleSpec(name="test.app_1.__app__", loader=None)
        app_1 = Application()  # No dependencies
        app_1_app_module.application = app_1

        app_2_module = ModuleType("test.app_2")
        app_2_module.__spec__ = ModuleSpec(name="test.app_2", loader=None)
        app_2_app_module = ModuleType("test.app_2.__app__")
        app_2_app_module.__spec__ = ModuleSpec(name="test.app_2.__app__", loader=None)
        app_2 = Application()  # No dependencies
        app_2_app_module.application = app_2

        with patch.dict(
            "sys.modules",
            {
                "test.app_1": app_1_module,
                "test.app_1.__app__": app_1_app_module,
                "test.app_2": app_2_module,
                "test.app_2.__app__": app_2_app_module,
            },
        ):
            # Create registry with no dependencies
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.app_1")
            registry.add("test.app_2")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should succeed with backward compatibility
            builder = SystemBuilder(registry, config)
            system = await builder.abuild()

            # Verify system was built
            assert system is not None
            assert system.config is config
            assert system.dispatcher is not None

            # Cleanup
            await system.dispose()

    @pytest.mark.asyncio
    async def test_complex_valid_dependency_chain(self):
        """
        Test that SystemBuilder handles complex but valid dependency chains.

        Scenario: Multi-level dependencies (ui -> api -> storage).
        Expected: System builds successfully with correct initialization order.
        """
        # Create fake modules for dependency chain
        storage_module = ModuleType("test.storage")
        storage_module.__spec__ = ModuleSpec(name="test.storage", loader=None)
        storage_app_module = ModuleType("test.storage.__app__")
        storage_app_module.__spec__ = ModuleSpec(name="test.storage.__app__", loader=None)
        storage_app = Application()  # Base dependency
        storage_app_module.application = storage_app

        api_module = ModuleType("test.api")
        api_module.__spec__ = ModuleSpec(name="test.api", loader=None)
        api_app_module = ModuleType("test.api.__app__")
        api_app_module.__spec__ = ModuleSpec(name="test.api.__app__", loader=None)
        api_app = Application(dependencies=["storage"])
        api_app_module.application = api_app

        ui_module = ModuleType("test.ui")
        ui_module.__spec__ = ModuleSpec(name="test.ui", loader=None)
        ui_app_module = ModuleType("test.ui.__app__")
        ui_app_module.__spec__ = ModuleSpec(name="test.ui.__app__", loader=None)
        ui_app = Application(dependencies=["api"])
        ui_app_module.application = ui_app

        with patch.dict(
            "sys.modules",
            {
                "test.storage": storage_module,
                "test.storage.__app__": storage_app_module,
                "test.api": api_module,
                "test.api.__app__": api_app_module,
                "test.ui": ui_module,
                "test.ui.__app__": ui_app_module,
            },
        ):
            # Create registry with dependency chain
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.storage")
            registry.add("test.api")
            registry.add("test.ui")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should succeed
            builder = SystemBuilder(registry, config)
            system = await builder.abuild()

            # Verify system was built
            assert system is not None
            assert system.config is config

            # Cleanup
            await system.dispose()

    @pytest.mark.asyncio
    async def test_multiple_missing_dependencies_clear_error(self):
        """
        Test that missing dependencies produce clear error messages.

        Scenario: App depends on multiple missing dependencies.
        Expected: MissingDependencyError with clear indication of what's missing.
        """
        # Create fake module with multiple missing dependencies
        app_module = ModuleType("test.app")
        app_module.__spec__ = ModuleSpec(name="test.app", loader=None)
        app_app_module = ModuleType("test.app.__app__")
        app_app_module.__spec__ = ModuleSpec(name="test.app.__app__", loader=None)
        app = Application(dependencies=["storage", "cache", "auth"])
        app_app_module.application = app

        with patch.dict(
            "sys.modules",
            {
                "test.app": app_module,
                "test.app.__app__": app_app_module,
            },
        ):
            # Create registry without any dependencies
            registry = ApplicationsRegistry(namespaces=["test"])
            registry.add("test.app")

            # Create minimal configuration
            config = GlobalSettings(applications={})

            # Build system - should fail with clear error
            builder = SystemBuilder(registry, config)
            with pytest.raises(MissingDependencyError) as exc_info:
                await builder.abuild()

            # Verify error message mentions the missing dependency
            error_message = str(exc_info.value)
            assert "app" in error_message
            assert any(dep in error_message for dep in ["storage", "cache", "auth"])

"""
Unit tests for application dependency resolution with topological sorting.

This module tests the dependency resolution mechanism for applications in the registry.
Applications can declare dependencies on other applications, and the registry must:
1. Validate that all dependencies exist
2. Detect circular dependencies
3. Order applications topologically based on their dependencies
"""

import pytest

from harp.config import Application, ApplicationsRegistry
from harp.errors import CircularDependencyError, MissingDependencyError


class ApplicationsRegistryMock(ApplicationsRegistry):
    """Mock registry that allows direct addition of applications without module loading."""

    def add_mock(self, name, impl):
        """Add an application directly to the registry without module resolution."""
        self._applications[name] = impl


class TestDependencyValidation:
    """
    Tests for validating that all declared dependencies exist in the registry.

    When an application declares dependencies, the registry must ensure those
    dependencies are actually registered and enabled.
    """

    def test_single_missing_dependency_raises_error(self):
        """
        Test that an application with a missing dependency raises MissingDependencyError.

        Scenario:
        - Application 'proxy' declares dependency on 'storage'
        - 'storage' is not in the registry
        - Should raise error with clear message
        """
        registry = ApplicationsRegistryMock()

        # Add proxy with dependency on storage (which doesn't exist)
        proxy_app = Application(dependencies=["storage"])
        registry.add_mock("proxy", proxy_app)

        with pytest.raises(
            MissingDependencyError, match="Application 'proxy' requires 'storage' but it is not enabled"
        ):
            registry.validate_dependencies()

    def test_multiple_missing_dependencies_raises_error_listing_all(self):
        """
        Test that multiple missing dependencies are reported together.

        Scenario:
        - Application 'proxy' declares dependencies on 'storage' and 'http_client'
        - Neither exists in registry
        - Should list all missing dependencies in error message
        """
        registry = ApplicationsRegistryMock()

        proxy_app = Application(dependencies=["storage", "http_client"])
        registry.add_mock("proxy", proxy_app)

        with pytest.raises(MissingDependencyError) as exc_info:
            registry.validate_dependencies()

        # Error message should mention both missing dependencies
        error_message = str(exc_info.value)
        assert "storage" in error_message
        assert "http_client" in error_message
        assert "proxy" in error_message

    def test_all_dependencies_exist_no_error(self):
        """
        Test that validation passes when all dependencies exist.

        Scenario:
        - Application 'proxy' depends on 'storage'
        - Both are in registry
        - Validation should pass without error
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        proxy_app = Application(dependencies=["storage"])

        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)

        # Should not raise any error
        registry.validate_dependencies()

    def test_empty_dependencies_list_no_error(self):
        """
        Test that apps with empty dependency lists validate successfully.

        Scenario:
        - Application has dependencies=[]
        - Should be treated same as no dependencies
        """
        registry = ApplicationsRegistryMock()

        app = Application(dependencies=[])
        registry.add_mock("test_app", app)

        # Should not raise any error
        registry.validate_dependencies()

    def test_no_dependencies_attribute_no_error(self):
        """
        Test backward compatibility: apps without dependencies attribute work.

        Scenario:
        - Application created without dependencies parameter (defaults to [])
        - Should validate successfully
        """
        registry = ApplicationsRegistryMock()

        app = Application()  # No dependencies parameter
        registry.add_mock("test_app", app)

        # Should not raise any error
        registry.validate_dependencies()

    def test_partial_dependencies_missing(self):
        """
        Test when some but not all dependencies are missing.

        Scenario:
        - Application 'dashboard' depends on 'proxy' and 'storage'
        - Only 'storage' exists
        - Should report 'proxy' as missing
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        dashboard_app = Application(dependencies=["proxy", "storage"])

        registry.add_mock("storage", storage_app)
        registry.add_mock("dashboard", dashboard_app)

        with pytest.raises(MissingDependencyError, match="proxy"):
            registry.validate_dependencies()


class TestTopologicalSorting:
    """
    Tests for ordering applications based on their dependencies.

    Applications must be loaded in dependency order: if A depends on B,
    then B must be loaded before A. This requires topological sorting.
    """

    def test_simple_chain_ordering(self):
        """
        Test simple dependency chain is ordered correctly.

        Scenario:
        - A depends on B
        - B depends on C
        - C has no dependencies
        - Order should be: [C, B, A]
        """
        registry = ApplicationsRegistryMock()

        app_c = Application()
        app_b = Application(dependencies=["c"])
        app_a = Application(dependencies=["b"])

        # Add in reverse order to ensure sorting happens
        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)
        registry.add_mock("c", app_c)

        registry.resolve_dependencies()

        # After resolution, registry should be ordered by dependencies
        ordered_names = list(registry.keys())
        assert ordered_names == ["c", "b", "a"]

    def test_complex_graph_with_shared_dependencies(self):
        """
        Test complex dependency graph with shared dependencies.

        Scenario:
        - 'dashboard' depends on 'proxy' and 'storage'
        - 'proxy' depends on 'http_client' and 'storage'
        - 'http_client' depends on 'storage'
        - 'storage' has no dependencies

        Valid ordering (storage first, dashboard last):
        - ['storage', 'http_client', 'proxy', 'dashboard']
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        http_client_app = Application(dependencies=["storage"])
        proxy_app = Application(dependencies=["http_client", "storage"])
        dashboard_app = Application(dependencies=["proxy", "storage"])

        # Add in random order
        registry.add_mock("dashboard", dashboard_app)
        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)
        registry.add_mock("http_client", http_client_app)

        registry.resolve_dependencies()

        ordered_names = list(registry.keys())

        # Verify topological ordering constraints
        assert ordered_names.index("storage") < ordered_names.index("http_client")
        assert ordered_names.index("storage") < ordered_names.index("proxy")
        assert ordered_names.index("storage") < ordered_names.index("dashboard")
        assert ordered_names.index("http_client") < ordered_names.index("proxy")
        assert ordered_names.index("proxy") < ordered_names.index("dashboard")

    def test_apps_without_dependencies_maintain_relative_order(self):
        """
        Test that apps without dependencies keep their original relative order.

        Scenario:
        - Apps A, B, C have no dependencies
        - They should maintain their registration order
        """
        registry = ApplicationsRegistryMock()

        app_a = Application()
        app_b = Application()
        app_c = Application()

        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)
        registry.add_mock("c", app_c)

        registry.resolve_dependencies()

        ordered_names = list(registry.keys())
        assert ordered_names == ["a", "b", "c"]

    def test_mixed_dependent_and_independent_apps(self):
        """
        Test ordering with both dependent and independent applications.

        Scenario:
        - 'independent1' and 'independent2' have no dependencies
        - 'dependent' depends on 'base'
        - 'base' has no dependencies

        Expected: base before dependent, independents maintain order
        """
        registry = ApplicationsRegistryMock()

        independent1_app = Application()
        base_app = Application()
        dependent_app = Application(dependencies=["base"])
        independent2_app = Application()

        registry.add_mock("independent1", independent1_app)
        registry.add_mock("dependent", dependent_app)
        registry.add_mock("base", base_app)
        registry.add_mock("independent2", independent2_app)

        registry.resolve_dependencies()

        ordered_names = list(registry.keys())

        # base must come before dependent
        assert ordered_names.index("base") < ordered_names.index("dependent")

        # independent apps maintain relative order
        assert ordered_names.index("independent1") < ordered_names.index("independent2")

    def test_empty_registry_resolves_without_error(self):
        """
        Test that resolving dependencies on empty registry doesn't fail.

        Scenario:
        - Registry has no applications
        - resolve_dependencies() should complete without error
        """
        registry = ApplicationsRegistryMock()

        # Should not raise any error
        registry.resolve_dependencies()

        assert len(registry) == 0

    def test_single_app_no_dependencies(self):
        """
        Test single application with no dependencies.

        Scenario:
        - One app with no dependencies
        - Should remain in registry unchanged
        """
        registry = ApplicationsRegistryMock()

        app = Application()
        registry.add_mock("solo", app)

        registry.resolve_dependencies()

        ordered_names = list(registry.keys())
        assert ordered_names == ["solo"]

    def test_internal_applications_dict_is_reordered(self):
        """
        Test that the internal _applications dict is actually reordered.

        Scenario:
        - Registry has apps in wrong order
        - After resolve_dependencies(), _applications dict should reflect new order
        - Iteration over registry should yield apps in dependency order
        """
        registry = ApplicationsRegistryMock()

        app_b = Application(dependencies=["a"])
        app_a = Application()

        # Add in wrong order (b before a)
        registry.add_mock("b", app_b)
        registry.add_mock("a", app_a)

        # Before resolution
        assert list(registry.keys()) == ["b", "a"]

        registry.resolve_dependencies()

        # After resolution, should be dependency-ordered
        assert list(registry.keys()) == ["a", "b"]

        # Verify _applications dict is actually reordered
        assert list(registry._applications.keys()) == ["a", "b"]


class TestCircularDependencies:
    """
    Tests for detecting circular dependencies in the application graph.

    Circular dependencies are invalid and must be detected with clear
    error messages showing the cycle.
    """

    def test_simple_two_app_cycle(self):
        """
        Test detection of simple A→B→A cycle.

        Scenario:
        - App A depends on B
        - App B depends on A
        - Should raise CircularDependencyError with cycle path
        """
        registry = ApplicationsRegistryMock()

        app_a = Application(dependencies=["b"])
        app_b = Application(dependencies=["a"])

        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)

        with pytest.raises(CircularDependencyError, match="Circular dependency detected.*a.*b.*a"):
            registry.resolve_dependencies()

    def test_longer_cycle_three_apps(self):
        """
        Test detection of longer cycle A→B→C→A.

        Scenario:
        - App A depends on B
        - App B depends on C
        - App C depends on A
        - Should detect and report the full cycle
        """
        registry = ApplicationsRegistryMock()

        app_a = Application(dependencies=["b"])
        app_b = Application(dependencies=["c"])
        app_c = Application(dependencies=["a"])

        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)
        registry.add_mock("c", app_c)

        with pytest.raises(CircularDependencyError) as exc_info:
            registry.resolve_dependencies()

        # Error message should show the cycle
        error_message = str(exc_info.value)
        assert "Circular dependency detected" in error_message
        # Should mention all apps in cycle
        assert "a" in error_message
        assert "b" in error_message
        assert "c" in error_message

    def test_self_dependency(self):
        """
        Test detection of self-dependency (app depends on itself).

        Scenario:
        - App A depends on A
        - Should be detected as circular dependency
        """
        registry = ApplicationsRegistryMock()

        app_a = Application(dependencies=["a"])
        registry.add_mock("a", app_a)

        with pytest.raises(CircularDependencyError, match="a"):
            registry.resolve_dependencies()

    def test_cycle_with_valid_dependencies(self):
        """
        Test cycle detection in graph with both valid and circular deps.

        Scenario:
        - Apps A, B, C form valid chain (A→B→C)
        - Apps D and E form cycle (D→E→D)
        - Should detect the D-E cycle
        """
        registry = ApplicationsRegistryMock()

        app_c = Application()
        app_b = Application(dependencies=["c"])
        app_a = Application(dependencies=["b"])
        app_d = Application(dependencies=["e"])
        app_e = Application(dependencies=["d"])

        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)
        registry.add_mock("c", app_c)
        registry.add_mock("d", app_d)
        registry.add_mock("e", app_e)

        with pytest.raises(CircularDependencyError) as exc_info:
            registry.resolve_dependencies()

        error_message = str(exc_info.value)
        # Should mention the cycle participants
        assert "d" in error_message and "e" in error_message

    def test_indirect_cycle_four_apps(self):
        """
        Test detection of longer indirect cycle.

        Scenario:
        - A→B→C→D→B (cycle from B back to B)
        - Should detect the B→C→D→B cycle
        """
        registry = ApplicationsRegistryMock()

        app_a = Application(dependencies=["b"])
        app_b = Application(dependencies=["c"])
        app_c = Application(dependencies=["d"])
        app_d = Application(dependencies=["b"])  # Creates cycle back to b

        registry.add_mock("a", app_a)
        registry.add_mock("b", app_b)
        registry.add_mock("c", app_c)
        registry.add_mock("d", app_d)

        with pytest.raises(CircularDependencyError) as exc_info:
            registry.resolve_dependencies()

        error_message = str(exc_info.value)
        # All cycle participants should be mentioned
        assert "b" in error_message
        assert "c" in error_message
        assert "d" in error_message


class TestEdgeCases:
    """
    Tests for edge cases and backward compatibility.

    Ensures that the dependency resolution feature doesn't break
    existing functionality and handles corner cases gracefully.
    """

    def test_backward_compatibility_apps_without_dependencies(self):
        """
        Test that existing apps without dependencies continue to work.

        Scenario:
        - Multiple apps, none declare dependencies
        - Should work exactly as before (maintain order)
        """
        registry = ApplicationsRegistryMock()

        # Apps created the old way (no dependencies parameter)
        storage_app = Application()
        proxy_app = Application()
        dashboard_app = Application()

        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)
        registry.add_mock("dashboard", dashboard_app)

        # Both methods should work without error
        registry.validate_dependencies()
        registry.resolve_dependencies()

        # Order should be maintained
        assert list(registry.keys()) == ["storage", "proxy", "dashboard"]

    def test_all_apps_depend_on_common_base(self):
        """
        Test diamond dependency pattern with shared base.

        Scenario:
        - 'storage' has no dependencies (base)
        - 'http_client', 'proxy', 'dashboard' all depend on 'storage'
        - 'storage' should be first, others can be in any order after
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        http_client_app = Application(dependencies=["storage"])
        proxy_app = Application(dependencies=["storage"])
        dashboard_app = Application(dependencies=["storage"])

        registry.add_mock("dashboard", dashboard_app)
        registry.add_mock("http_client", http_client_app)
        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)

        registry.resolve_dependencies()

        ordered_names = list(registry.keys())

        # storage must be first
        assert ordered_names[0] == "storage"

        # Others can be in any order but all after storage
        assert set(ordered_names[1:]) == {"http_client", "proxy", "dashboard"}

    def test_dependency_on_app_with_empty_list(self):
        """
        Test app depending on another app that has empty dependencies list.

        Scenario:
        - App A has dependencies=[]
        - App B depends on A
        - Should work correctly (A before B)
        """
        registry = ApplicationsRegistryMock()

        app_a = Application(dependencies=[])
        app_b = Application(dependencies=["a"])

        registry.add_mock("b", app_b)
        registry.add_mock("a", app_a)

        registry.resolve_dependencies()

        assert list(registry.keys()) == ["a", "b"]

    def test_case_sensitivity_in_dependencies(self):
        """
        Test that dependency names are case-sensitive.

        Scenario:
        - App 'storage' exists
        - App 'proxy' depends on 'Storage' (capital S)
        - Should be treated as missing dependency
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        proxy_app = Application(dependencies=["Storage"])  # Wrong case

        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)

        with pytest.raises(MissingDependencyError, match="Storage"):
            registry.validate_dependencies()

    def test_whitespace_in_dependency_names_not_trimmed(self):
        """
        Test that dependency names are used exactly as provided.

        Scenario:
        - App 'proxy' depends on ' storage ' (with spaces)
        - App 'storage' exists (no spaces)
        - Should be treated as missing dependency
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        proxy_app = Application(dependencies=[" storage "])  # With spaces

        registry.add_mock("storage", storage_app)
        registry.add_mock("proxy", proxy_app)

        with pytest.raises(MissingDependencyError):
            registry.validate_dependencies()


class TestAutoloadDependencies:
    """
    Tests for automatic dependency loading when adding applications.

    When autoload_dependencies=True, the add() method should automatically
    add any declared dependencies that aren't already in the registry.
    """

    def test_autoload_single_dependency(self):
        """
        Test that a single dependency is automatically loaded.

        Scenario:
        - http_cache depends on http_client
        - Add http_cache with autoload_dependencies=True
        - http_client should be automatically added
        """
        registry = ApplicationsRegistry(namespaces=["harp_apps"])

        # Add http_cache with autoload_dependencies=True
        # http_cache declares dependency on http_client
        registry.add("http_cache", autoload_dependencies=True)

        # Both http_cache and http_client should be in registry
        assert "http_cache" in registry
        assert "http_client" in registry

    def test_autoload_disabled_by_default(self):
        """
        Test that autoload_dependencies defaults to False.

        Scenario:
        - http_cache depends on http_client
        - Add http_cache without autoload_dependencies parameter
        - Only http_cache should be added (not http_client)
        """
        registry = ApplicationsRegistry(namespaces=["harp_apps"])

        # Add http_cache without autoload_dependencies
        registry.add("http_cache")

        # Only http_cache should be in registry
        assert "http_cache" in registry
        assert "http_client" not in registry

    def test_autoload_transitive_dependencies(self):
        """
        Test that transitive dependencies are automatically loaded.

        Scenario:
        - http_cache depends on http_client
        - http_client depends on storage (hypothetically)
        - Add http_cache with autoload_dependencies=True
        - All three should be in registry
        """
        registry = ApplicationsRegistry(namespaces=["harp_apps"])

        # Add http_cache with autoload_dependencies=True
        registry.add("http_cache", autoload_dependencies=True)

        # Verify http_cache was added
        assert "http_cache" in registry
        assert "http_client" in registry

    def test_autoload_no_duplicate_loading(self):
        """
        Test that already-loaded apps aren't reloaded.

        Scenario:
        - http_client is already in registry
        - Add http_cache (depends on http_client) with autoload_dependencies=True
        - http_client shouldn't be added again
        """
        registry = ApplicationsRegistry(namespaces=["harp_apps"])

        # Pre-add http_client
        registry.add("http_client")
        assert "http_client" in registry

        # Add http_cache with autoload_dependencies
        registry.add("http_cache", autoload_dependencies=True)

        # Both should be in registry (no duplicate)
        assert "http_cache" in registry
        assert "http_client" in registry
        assert len([name for name in registry if name == "http_client"]) == 1


class TestIntegrationScenarios:
    """
    Tests for realistic integration scenarios combining validation and resolution.

    These tests verify that the complete workflow (validate then resolve) works
    correctly for real-world application dependency graphs.
    """

    def test_complete_workflow_valid_dependencies(self):
        """
        Test complete validate + resolve workflow with valid dependencies.

        Scenario:
        - Complex but valid dependency graph
        - Validate passes
        - Resolve produces correct order
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        http_client_app = Application(dependencies=["storage"])
        proxy_app = Application(dependencies=["http_client", "storage"])
        dashboard_app = Application(dependencies=["proxy"])

        registry.add_mock("dashboard", dashboard_app)
        registry.add_mock("proxy", proxy_app)
        registry.add_mock("storage", storage_app)
        registry.add_mock("http_client", http_client_app)

        # Complete workflow
        registry.validate_dependencies()
        registry.resolve_dependencies()

        ordered_names = list(registry.keys())

        # Verify complete topological ordering
        assert ordered_names.index("storage") < ordered_names.index("http_client")
        assert ordered_names.index("http_client") < ordered_names.index("proxy")
        assert ordered_names.index("proxy") < ordered_names.index("dashboard")

    def test_validation_fails_before_resolution_attempted(self):
        """
        Test that validation failure prevents resolution attempt.

        Scenario:
        - App has missing dependency
        - validate_dependencies() should fail
        - resolve_dependencies() may not be called if validation fails first
        """
        registry = ApplicationsRegistryMock()

        proxy_app = Application(dependencies=["missing"])
        registry.add_mock("proxy", proxy_app)

        with pytest.raises(MissingDependencyError):
            registry.validate_dependencies()

        # If we skip validation and go straight to resolution,
        # it should also fail (defensive programming)
        with pytest.raises((MissingDependencyError, CircularDependencyError, KeyError)):
            registry.resolve_dependencies()

    def test_real_world_harp_apps_structure(self):
        """
        Test realistic HARP application dependency structure.

        Scenario: Typical HARP setup with:
        - storage (base, no deps)
        - http_client (depends on storage for caching)
        - proxy (depends on http_client and storage)
        - dashboard (depends on proxy and storage)
        - rules (depends on storage)

        Expected order respects all dependencies.
        """
        registry = ApplicationsRegistryMock()

        storage_app = Application()
        http_client_app = Application(dependencies=["storage"])
        rules_app = Application(dependencies=["storage"])
        proxy_app = Application(dependencies=["http_client", "storage"])
        dashboard_app = Application(dependencies=["proxy", "storage"])

        # Add in registration order (not dependency order)
        registry.add_mock("dashboard", dashboard_app)
        registry.add_mock("rules", rules_app)
        registry.add_mock("proxy", proxy_app)
        registry.add_mock("http_client", http_client_app)
        registry.add_mock("storage", storage_app)

        registry.validate_dependencies()
        registry.resolve_dependencies()

        ordered_names = list(registry.keys())

        # storage must be first
        assert ordered_names[0] == "storage"

        # All dependencies must be satisfied
        assert ordered_names.index("storage") < ordered_names.index("http_client")
        assert ordered_names.index("storage") < ordered_names.index("rules")
        assert ordered_names.index("storage") < ordered_names.index("proxy")
        assert ordered_names.index("storage") < ordered_names.index("dashboard")
        assert ordered_names.index("http_client") < ordered_names.index("proxy")
        assert ordered_names.index("proxy") < ordered_names.index("dashboard")

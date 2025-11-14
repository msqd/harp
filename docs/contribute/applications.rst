Applications
============

HARP applications are Python packages that integrate with the system through a standard protocol. Both core features
and third-party extensions use the same protocol.

An application is a Python package with an ``__app__.py`` file that defines how it hooks into the system.

Basic Structure
:::::::::::::::

To create a HARP application, add an ``__app__.py`` file to your Python package:

.. code-block:: python

    from harp.config import Application

    application = Application()

Applications usually also need settings.


Configuring Settings
::::::::::::::::::::

Define your settings in a ``settings.py`` file:

.. literalinclude:: ../../harp_apps/acme/settings.py

.. versionadded:: 0.10
   All application settings must inherit from ``ApplicationSettingsMixin``.

Then reference them in ``__app__.py``:

.. code-block:: python

    from harp.config import Application
    from .settings import AcmeSettings


    application = Application(
        settings_type=AcmeSettings,
    )

Test your settings:

.. literalinclude:: ../../harp_apps/acme/tests/test_settings.py

.. important::
   ``ApplicationSettingsMixin`` must be the first base class in the inheritance chain.


Declaring Dependencies
::::::::::::::::::::::

.. versionadded:: 0.10
   Applications should now declare dependencies to ensure correct initialization order.

Applications can declare dependencies on other applications. The system validates these dependencies at startup and
initializes applications in the correct order using topological sorting.

Basic Usage
-----------

Declare dependencies by passing a list of application names:

.. code-block:: python

    from harp.config import Application
    from .settings import ProxySettings

    application = Application(
        settings_type=ProxySettings,
        dependencies=["storage", "http_client"],
    )

The system ensures:

- All declared dependencies are enabled
- Applications initialize in dependency order (dependencies before dependents)
- Circular dependencies are detected and rejected

Dependency Resolution
---------------------

At startup, the system validates dependencies, detects cycles, and initializes applications in topological order.

Error Handling
--------------

The system fails fast at startup if dependencies are invalid:

**Missing dependency:**

.. code-block:: text

    MissingDependencyError: Application 'proxy' requires 'storage' but it is not enabled

**Circular dependency:**

.. code-block:: text

    CircularDependencyError: Circular dependency detected: proxy → storage → proxy

Best Practices
--------------

- Declare only direct dependencies (the system resolves transitive dependencies automatically)
- Use simple application names (e.g., ``storage``, not ``harp_apps.storage``)
- Keep dependency chains shallow when possible
- Applications without dependencies work unchanged (backward compatible)

Example Dependency Structure
-----------------------------

A typical HARP setup might look like:

.. code-block:: text

    storage (no dependencies)
    ├── http_client (depends on storage)
    │   └── proxy (depends on http_client, storage)
    │       ├── dashboard (depends on proxy, storage)
    │       └── rules (depends on storage)

The system automatically determines the initialization order: ``storage``, ``http_client``, ``proxy``, then ``dashboard`` and ``rules`` in any order.

Testing with Partial Systems
-----------------------------

When writing tests, you may need to build partial systems with only specific applications enabled. Since dependency validation is enabled by default, tests that build incomplete systems will fail if required dependencies are missing.

Use the ``validate_dependencies=False`` parameter to bypass validation in tests:

.. code-block:: python

    from harp.config import ConfigurationBuilder

    async def test_my_feature():
        # Build partial system for isolated testing
        system = await ConfigurationBuilder(
            {"applications": ["http_client", "storage"]},
            use_default_applications=False,
        ).abuild_system(validate_dependencies=False)

        # Test specific behavior without loading all dependencies
        http_client = system.provider.get("http_client")
        assert http_client is not None

**Important Notes:**

- Only use ``validate_dependencies=False`` in tests for partial systems
- Production code should always validate dependencies (the default behavior)
- Tests for the full system should keep validation enabled to catch real dependency issues
- Command-line tools that build partial systems may also need this parameter


Application Lifecycle
:::::::::::::::::::::

Applications interact with the system through lifecycle hooks. All hooks are async functions that receive an event object.


.. _on_bind:
On Bind
-------

Called during system setup. Register services and dependencies here.

.. code-block:: python

    from harp.config import Application, OnBindEvent

    async def on_bind(event: OnBindEvent):
        ...

    application = Application(
        ...,
        on_bind=on_bind,
    )

Reference: :class:`harp.config.OnBindEvent`


.. _on_bound:
On Bound
--------

Called after services are registered. Access and configure service instances here.

.. code-block:: python

    from harp.config import Application, OnBoundEvent

    async def on_bound(event: OnBoundEvent):
        ...

    application = Application(
        ...,
        on_bound=on_bound,
    )

Reference: :class:`harp.config.OnBoundEvent`


.. _on_ready:
On Ready
--------

Called when the system starts. All services are ready.

.. code-block:: python

    from harp.config import Application, OnReadyEvent

    async def on_ready(event: OnReadyEvent):
        ...

    application = Application(
        ...,
        on_ready=on_ready,
    )

Reference: :class:`harp.config.OnReadyEvent`


.. _on_shutdown:
On Shutdown
-----------

Called during system shutdown. Clean up resources here.

Shutdown events are dispatched in **reverse** order - the first application initialized is the last to shut down.

.. code-block:: python

    from harp.config import Application, OnShutdownEvent

    async def on_shutdown(event: OnShutdownEvent):
        ...

    application = Application(
        ...,
        on_shutdown=on_shutdown,
    )

Reference: :class:`harp.config.OnShutdownEvent`

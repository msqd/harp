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
   Applications can declare dependencies to ensure correct initialization order.

Applications declare dependencies as a list. At startup, the system validates all dependencies exist, detects cycles, and initializes applications in topological order.

.. code-block:: python

    from harp.config import Application
    from .settings import ProxySettings

    application = Application(
        settings_type=ProxySettings,
        dependencies=["storage", "http_client"],  # Simple list of app names
    )

**Best practices:**

- Declare only direct dependencies (transitive dependencies are resolved automatically)
- Use simple names (``storage``, not ``harp_apps.storage``)
- Applications without dependencies work unchanged

**Error examples:**

.. code-block:: text

    # Missing dependency
    MissingDependencyError: Application 'proxy' requires 'storage' but it is not enabled

    # Circular dependency
    CircularDependencyError: Circular dependency detected: proxy → storage → proxy

**Testing with partial systems:**

Tests building incomplete systems can bypass validation with ``validate_dependencies=False``:

.. code-block:: python

    system = await ConfigurationBuilder(
        {"applications": ["http_client", "storage"]},
        use_default_applications=False,
    ).abuild_system(validate_dependencies=False)  # Skip validation for tests

.. warning::
   Only use ``validate_dependencies=False`` in tests. Production code should always validate (default behavior).

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

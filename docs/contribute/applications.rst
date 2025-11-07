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

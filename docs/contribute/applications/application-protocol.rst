Application Protocol
====================

The HARP Application Protocol enables writing plug-and-play Python packages to enhance core functionalities.

An application is essentially a Python package with additional files that integrate it with the HARP framework.

Basic Structure
:::::::::::::::

A standard Python package has a directory containing an ``__init__.py`` file. To transform this package into a HARP
application, you need to add an ``__app__.py`` file at the root. This file contains the application's definition.

Example ``__app__.py``:

.. code-block:: python

    from harp.config import Application

    application = Application()

This setup is the bare minimum. However, applications usually require more features, such as settings.


Configuring Settings
::::::::::::::::::::

Applications often need custom settings. You can define these settings in a class, typically stored in a ``settings.py``
file at the package root.

1. Define your settings class in settings.py.
2. Include this class in your application definition in ``__app__.py``.

Example ``settings.py``:

.. literalinclude:: ../../../harp_apps/acme/settings.py

Example ``__app__.py`` update:

.. code-block:: python

    from harp.config import Application
    from .settings import AcmeSettings


    application = Application(
        settings_type=AcmeSettings,
    )

The settings class should:

- Be instantiable without arguments for default settings.
- Accept keyword arguments for custom settings.
- Convert to a dictionary via :func:`harp.config.asdict`.

Let's write a simple test to check that.

.. literalinclude:: ../../../harp_apps/acme/tests/test_settings.py


Application Lifecycle
:::::::::::::::::::::

To have a real purpose, an application should interact with the core system through lifecycle hooks.

All hooks are python coroutines, taking a specific :class:`whistle.Event` instance as argument.

Hooks must be registered in the application definition.


On Bind
-------

Triggered during system setup but before service instances are created. Ideal for defining services and dependencies.

.. code-block:: python

    from harp.config import OnBindEvent

    async def on_bind(event: OnBindEvent):
        ...

Reference: :class:`harp.config.OnBindEvent`


On Bound
--------

Occurs when the system can instantiate services. Use this to access and manipulate service instances.

.. code-block:: python

    from harp.config import OnBoundEvent

    async def on_bound(event: OnBoundEvent):
        ...

Reference: :class:`harp.config.OnBoundEvent`


On Ready
--------

Called when the system starts, after all services are ready. A good place to add ASGI middlewares.

.. code-block:: python

    from harp.config import OnReadyEvent

    async def on_ready(event: OnReadyEvent):
        ...

Reference: :class:`harp.config.OnReadyEvent`


On Shutdown
-----------

Invoked during system shutdown, allowing for cleanup and resource release.

Unlike other events, the shutdown events will be dispatched in applications **reverse** order, so that the first
initialized application is the last to be shutdown.

.. code-block:: python

    from harp.config import OnShutdownEvent

    async def on_shutdown(event: OnShutdownEvent):
        ...

Reference: :class:`harp.config.OnShutdownEvent`


Full Example
::::::::::::

``__app__.py``
--------------

.. literalinclude:: ../../../harp_apps/acme/__app__.py

``settings.py``
---------------

.. literalinclude:: ../../../harp_apps/acme/settings.py

``tests/test_settings.py``
--------------------------

.. literalinclude:: ../../../harp_apps/acme/tests/test_settings.py

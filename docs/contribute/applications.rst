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
file at the application's package root.

1. Define your settings class in settings.py.
2. Include this class in your application definition in ``__app__.py``.

Example ``settings.py``:

.. literalinclude:: ../../harp_apps/acme/settings.py

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

For convenience, we provide a :class:`harp.config.Configurable` class that you can inherit from to implement your
settings. It is a subclass of pydantic's :class:`BaseModel <pydantic.BaseModel>` and provides a few additional methods.

Please refer to the pydantic's documentation for more information on how to use it.


Application Lifecycle
:::::::::::::::::::::

To have a real purpose, an application should interact with the core system through lifecycle hooks.

All hooks are python coroutines, taking a specific :class:`whistle.Event` instance as argument.

Hooks must be registered in the application definition.


.. _on_bind:
On Bind
-------

Triggered during system setup but before service instances are created. Ideal for defining services and dependencies.

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

Occurs when the system can instantiate services. Use this to access and manipulate service instances.

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

Called when the system starts, after all services are ready. A good place to add ASGI middlewares.

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

Invoked during system shutdown, allowing for cleanup and resource release.

Unlike other events, the shutdown events will be dispatched in applications **reverse** order, so that the first
initialized application is the last to be shutdown.

.. code-block:: python

    from harp.config import Application, OnShutdownEvent

    async def on_shutdown(event: OnShutdownEvent):
        ...

    application = Application(
        ...,
        on_shutdown=on_shutdown,
    )

Reference: :class:`harp.config.OnShutdownEvent`


Full Example
::::::::::::

You can find this example in the `ACME application <https://github.com/msqd/harp/tree/0.7/harp_apps/acme>`_, which sole
purpose is to demonstrate the application protocol.

``__app__.py``
--------------

.. literalinclude:: ../../harp_apps/acme/__app__.py

``settings.py``
---------------

.. literalinclude:: ../../harp_apps/acme/settings.py

``tests/test_settings.py``
--------------------------

.. literalinclude:: ../../harp_apps/acme/tests/test_settings.py

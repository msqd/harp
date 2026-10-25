Mounting an ASGI application
============================

Some libraries are ASGI applications themselves (static files middleware, the MCP SDK...). Rather than translating
them into HARP's request/response model, mount them with :class:`harp.controllers.AsgiMountController`. It hands the
application the raw ASGI ``receive`` and ``send``, so responses (including streaming ones) go straight to the client,
and the kernel skips its own response step.

.. code-block:: python

    from whistle import IAsyncEventDispatcher

    from harp.controllers import AsgiMountController

    mount = AsgiMountController(my_asgi_app, prefix="/mcp")

    # in your application's on_bound handler
    event.resolver.add_controller(mount, name="mcp", port=4080)
    mount.register(event.provider.get(IAsyncEventDispatcher))

What the mounted application sees
---------------------------------

- The original scope, with ``path`` (and ``raw_path``) relative to the prefix and ``root_path`` extended by it:
  ``/mcp/messages`` reaches the application as ``/messages``, with ``root_path`` ``/mcp``.
- A request outside the prefix is answered with a 404, without reaching the application. The prefix matches on whole
  path segments (``/mcpx`` is not under ``/mcp``).
- An empty prefix (the default) mounts at the root and leaves the path alone.

Lifespan
--------

By default, the mounted application receives ``lifespan.startup`` and ``lifespan.shutdown`` along with HARP's own, once
:meth:`~harp.controllers.AsgiMountController.register` has been called with the kernel's dispatcher. An application
that does not support the lifespan scope is simply served without it. Pass ``lifespan=False`` to skip it entirely.

The kernel always waits for ``lifespan.shutdown`` after startup, then fires ``core.stopped``. A failure in either phase
is reported to the server as ``lifespan.startup.failed`` or ``lifespan.shutdown.failed``. A mounted application that
fails to start fails the startup; one that fails while stopping is logged and the rest of the shutdown goes on.

Limits
------

Only HTTP is delegated: websockets are not supported yet.

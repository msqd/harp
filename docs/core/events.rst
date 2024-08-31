Events
======

HARP Core dispatches a few events.

Class Diagram
:::::::::::::


Configuration Events
::::::::::::::::::::

.. py:currentmodule:: harp.config.events

During the setup and teardown phase, the :mod:`harp.config` module dispatches events to allow applications and other
components to register themselves with the system.

You can add listeners to those events using the :doc:`Application Protocol </contribute/applications>`.


EVENT_BIND
----------

Dispatched by :meth:`SystemBuilder.dispatch_bind_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_bind_event>` during the assembly of core components on startup.

.. code:: python

    from harp.config.events import EVENT_BIND, OnBindEvent
    from whistle import IAsyncEventDispatcher

    async def on_bind(event: OnBindEvent):
        print("System is being bound")

    if __name__ == "__main__":
        # for example completeness only, you should use the system dispatcher
        dispatcher: IAsyncEventDispatcher = ...
        dispatcher.add_listener(EVENT_BIND, on_bind)

Dispatched as :attr:`EVENT_BIND` with a :class:`OnBindEvent` instance, its main purpose is to allow applications to
:ref:`define services on startup <on_bind>`.


EVENT_BOUND
-----------

Dispatched by :meth:`SystemBuilder.dispatch_bound_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_bound_event>` after the container has been compiled to a provider.
All service dependencies are resolved, instances can be requested from the provider.

.. code:: python

    from harp.config.events import EVENT_BOUND, OnBoundEvent
    from whistle import IAsyncEventDispatcher

    async def on_bound(event: OnBoundEvent):
        print("System is bound")

    if __name__ == "__main__":
        # for example completeness only, you should use the system dispatcher
        dispatcher: IAsyncEventDispatcher = ...
        dispatcher.add_listener(EVENT_BOUND, on_bound)

Dispatched as :attr:`EVENT_BOUND` with a :class:`OnBoundEvent` instance, its main purpose is to allow applications to
:ref:`instanciate and manipulate live services on startup <on_bound>`.


EVENT_READY
-----------

Dispatched by :meth:`SystemBuilder.dispatch_ready_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_ready_event>` after the system has been fully assembled and is
(about to be) ready to start processing requests.

.. code:: python

    from harp.config.events import EVENT_READY, OnReadyEvent
    from whistle import IAsyncEventDispatcher

    async def on_ready(event: OnReadyEvent):
        print("System is ready")

    if __name__ == "__main__":
        # for example completeness only, you should use the system dispatcher
        dispatcher: IAsyncEventDispatcher = ...
        dispatcher.add_listener(EVENT_READY, on_ready)

Dispatched as :attr:`EVENT_READY` with a :class:`OnReadyEvent` instance.

The :class:`ASGI Kernel <harp.asgi.ASGIKernel>` is available here, and this event is mostly used to
:ref:`decorate it with ASGI middlewares <on_ready>` (for example, Sentry integration).

EVENT_SHUTDOWN
--------------

Dispatched by :meth:`System.dispose(...) <harp.config.builders.system.System.dispose>` when the system is being shut
down.

.. code:: python

    from harp.config.events import EVENT_SHUTDOWN, OnShutdownEvent
    from whistle import IAsyncEventDispatcher

    async def on_shutdown(event: OnShutdownEvent):
        print("System is shutting down")

    if __name__ == "__main__":
        # for example completeness only, you should use the system dispatcher
        dispatcher: IAsyncEventDispatcher = ...
        dispatcher.add_listener(EVENT_SHUTDOWN, on_shutdown)

Dispatched as :attr:`EVENT_SHUTDOWN` with a :class:`OnShutdown` instance. This event purpose is to allow applications to
:ref:`clean up resources on shutdown <on_shutdown>`.


Class Diagram
-------------

.. graphviz:: events.config.dot


ASGI Events
:::::::::::

.. py:currentmodule:: harp.asgi.events

During the lifecycle of an ASGI Request, the :mod:`harp.asgi` module dispatches events to allow (low-level) applications
to process or filter inbound requests and outbound responses.

* :attr:`EVENT_CORE_STARTED` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when the "lifespan" ASGI
  message is received.

  It usually happens only once per process, and this is, as the ASGI protocol defines, the first ASGI message to go
  through the system.

  It is dispatched with a :class:`whistle.Event` instance, containing no context.

* :attr:`EVENT_CORE_REQUEST` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when an inbound
  :class:`HttpRequest <harp.http.HttpRequest>` is received, before anything is done with it.

  It is dispatched with a :class:`RequestEvent` instance with a reference to the :class:`HttpRequest
  <harp.http.HttpRequest>` instance.

  Listeners can use :meth:`event.set_controller(...) <RequestEvent.set_controller>`, bypassing further
  controller resolution. This can be used by middlewares that know how to handle the request entirely.

* :attr:`EVENT_CORE_CONTROLLER` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when a controller
  callable has been resolved by the kernel's :class:`controller resolver <harp.controllers.typing.IControllerResolver>`.

  It is used to eventually modify the controller, for example with decorators, or change it altogether.

  It is dispatched with a :class:`ControllerEvent` instance with a reference to the controller callable.

* :attr:`EVENT_CONTROLLER_VIEW` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when a controller
  callable has been called but it did not return an :class:`HttpResponse <harp.http.HttpResponse>`.

  It is used to implement custom response handlers, for example dictionaries return values.

  It is dispatched with a :class:`ControllerViewEvent` instance with a reference to the controller's return value.

  If after it has been fully dispatched, the event does not contain a response, then a HTTP 500 response is returned.

* :attr:`EVENT_CORE_RESPONSE` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when an outbound
  :class:`HttpResponse <harp.http.HttpResponse>` is about to be sent.

  It is dispatched with a :class:`ResponseEvent` instance with a reference to the :class:`HttpResponse
  <harp.http.HttpResponse>` instance.

  Listeners can use :attr:`event.response = ... <ResponseEvent.response>` event attribute to change the response.

.. todo:: Add sequence diagram

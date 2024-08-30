Events
======

HARP Core dispatches a few events.

Configuration Events
::::::::::::::::::::

.. py:currentmodule:: harp.config.events

During the setup and teardown phase, the :mod:`harp.config` module dispatches events to allow applications and other
components to register themselves with the system.

You can add listeners to those events using the :doc:`Application Protocol </contribute/applications>`.

* :attr:`EVENT_BIND` is dispatched by :meth:`SystemBuilder.dispatch_bind_event(...)
  <harp.config.builders.system.SystemBuilder.dispatch_bind_event>` during the assembly of core components, during the
  process setup.

  It happens after the configuration, dispatcher and container have been created and is a good place to load service
  definitions.

  It is dispatched with a :class:`OnBindEvent` instance.

* :attr:`EVENT_BOUND` is dispatched by :meth:`SystemBuilder.dispatch_bound_event(...)
  <harp.config.builders.system.SystemBuilder.dispatch_bound_event>` after the container has been compiled to a provider,
  meaning that all service dependencies are resolved and thus instances can be requested.

  It is dispatched with a :class:`OnBoundEvent` instance.

* :attr:`EVENT_READY` is dispatched by :meth:`SystemBuilder.dispatch_ready_event(...)
  <harp.config.builders.system.SystemBuilder.dispatch_ready_event>` after the system has been fully assembled and is
  ready to start processing requests.

  The :class:`ASGI Kernel <harp.asgi.ASGIKernel>` is available here, and this event is mostly used to replace it by a
  decorated version using ASGI middlewares that must run at a very low level (for example, Sentry integration).

  It is dispatched with a :class:`OnReadyEvent` instance.

* :attr:`EVENT_SHUTDOWN` is dispatched by :meth:`System.dispose(...)
  <harp.config.builders.system.System.dispose>` when the system is about to be shut down.

  It is dispatched with a :class:`OnShutdownEvent` instance.


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

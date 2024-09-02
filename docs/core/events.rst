Events
======

This document describes the :ref:`events <events>` dispatched by HARP Proxy's core.

You can read about the :doc:`concept and mechanics of the event-driven architecture
</contribute/events>` of HARP Proxy in the :doc:`contributor's guide </contribute/index>`.


Configuration Events
::::::::::::::::::::

.. py:currentmodule:: harp.config.events

During the setup and teardown phase, the :mod:`harp.config` module dispatches events to allow applications and other
components to register themselves with the system.

You can add listeners to those events using the :doc:`Application Protocol </contribute/applications>`.


EVENT_BIND
----------

Dispatched by :meth:`SystemBuilder.dispatch_bind_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_bind_event>` when the :ref:`container <service_container>` is
being configured.

Its main purpose is to allow :ref:`applications to define services <on_bind>`, by registering some :ref:`service
definitions <service_definitions>` with the :ref:`container <service_container>`.

Dispatched as :attr:`EVENT_BIND` with a :class:`OnBindEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_BIND` event:

    .. literalinclude:: ./examples/events.config.bind.py


EVENT_BOUND
-----------

Dispatched by :meth:`SystemBuilder.dispatch_bound_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_bound_event>` after the :ref:`container <service_container>` has
been compiled to a :ref:`provider <service_provider>`. At this point, all service dependencies are resolved, instances
can be requested from the :ref:`provider <service_provider>`.

Its main purpose is to allow applications to :ref:`instanciate and manipulate live services on startup <on_bound>`.

Dispatched as :attr:`EVENT_BOUND` with a :class:`OnBoundEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_BOUND` event:

    .. literalinclude:: ./examples/events.config.bound.py


EVENT_READY
-----------

Dispatched by :meth:`SystemBuilder.dispatch_ready_event(...)
<harp.config.builders.system.SystemBuilder.dispatch_ready_event>` after the :class:`system
<harp.config.builders.system.System>` has been fully assembled and is (about to be) ready to start processing requests.

Dispatched as :attr:`EVENT_READY` with a :class:`OnReadyEvent` instance.

The :class:`ASGI Kernel <harp.asgi.ASGIKernel>` is available here, and this event is mostly used to :ref:`decorate it
with ASGI middlewares <on_ready>` (e.g. :doc:`Sentry <../apps/contrib/sentry/index>` or :doc:`Prometheus
<../apps/contrib/prometheus/index>` integrations).

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_READY` event:

    .. literalinclude:: ./examples/events.config.ready.py


EVENT_SHUTDOWN
--------------

Dispatched by :meth:`System.dispose(...) <harp.config.builders.system.System.dispose>` when the system is being shut
down.

Dispatched as :attr:`EVENT_SHUTDOWN` with a :class:`OnShutdown` instance.

This event purpose is to allow applications to :ref:`clean up resources on shutdown <on_shutdown>`. For example, if
applications define background asynchronous tasks, it's a good idea to terminate them here.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_SHUTDOWN` event:

    .. literalinclude:: ./examples/events.config.shutdown.py


Sequence Diagram
----------------

.. todo:: Add sequence diagram


Class Diagram
-------------

.. raw:: html
    :file: events.config.svg


Core / ASGI Events
::::::::::::::::::

.. py:currentmodule:: harp.asgi.events

During the lifecycle of an ASGI Request, the :mod:`harp.asgi` module dispatches events to allow (low-level) applications
to process or filter inbound requests and outbound responses.

.. note::

    The ASGI events are rather low-level, and are usually only used to implement framework-level features by the HARP
    Core. You should not need to use them in your application code, or at least, it should not be the first thing you
    go for.

    If you need to hook into the request/response lifecycle, you are probably better of using either the :doc:`Proxy
    Events <../apps/proxy/events>` for inbound request processing (and their associated responses), or the :doc:`Http
    Client Events <../apps/http_client/events>` for outgoing requests (and their associated responses).


EVENT_CORE_STARTED
------------------

Dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when the "lifespan.startup" ASGI message is received.

It happens once per process, before any other ASGI messages are recevived.

Dispatched as :attr:`EVENT_CORE_STARTED` with a :class:`whistle.Event` instance (default event class that contains no
specific context).

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_CORE_STARTED` event:

    .. literalinclude:: ./examples/events.asgi.started.py

.. seealso::

    `ASGI Lifespan Protocol (from ASGI Specicication) <https://asgi.readthedocs.io/en/latest/specs/lifespan.html>`_


EVENT_CORE_REQUEST
------------------

Dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when an inbound :class:`HttpRequest
<harp.http.HttpRequest>` is received, before anything is done with it.

Listeners can use :meth:`event.set_controller(...) <RequestEvent.set_controller>`, bypassing further controller
resolution.

Dispatched as :attr:`EVENT_CORE_REQUEST` with a :class:`RequestEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_CORE_REQUEST` event:

    .. literalinclude:: ./examples/events.asgi.request.py


EVENT_CORE_CONTROLLER
---------------------

Dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when a controller callable has been resolved by the
kernel's :class:`controller resolver <harp.controllers.typing.IControllerResolver>`.

It is used to eventually modify the controller, for example with decorators, or change it altogether.

Dispatched as :attr:`EVENT_CORE_CONTROLLER` with a :class:`ControllerEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_CORE_CONTROLLER` event:

    .. literalinclude:: ./examples/events.asgi.controller.py


EVENT_CORE_VIEW
---------------

:attr:`EVENT_CORE_VIEW` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when a controller
callable has been called but it did not return an :class:`HttpResponse <harp.http.HttpResponse>`.

It is used to implement custom response handlers, for example dictionaries return values.

If after it has been fully dispatched, the event does not contain a response, then a HTTP 500 response is returned.

Dispatched as :attr:`EVENT_CORE_VIEW` with a :class:`ViewEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_CORE_VIEW` event:

    .. literalinclude:: ./examples/events.asgi.view.py


EVENT_CORE_RESPONSE
-------------------

:attr:`EVENT_CORE_RESPONSE` is dispatched by the :class:`ASGIKernel <harp.asgi.ASGIKernel>` when an outbound
:class:`HttpResponse <harp.http.HttpResponse>` is about to be sent.

Listeners can use :attr:`event.response = ... <ResponseEvent.response>` event attribute to change the response.

Dispatched as :attr:`EVENT_CORE_RESPONSE` with a :class:`ResponseEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_CORE_RESPONSE` event:

    .. literalinclude:: ./examples/events.asgi.response.py


Sequence Diagram
----------------

.. todo:: Add sequence diagram


Class Diagram
-------------

.. raw:: html
    :file: events.asgi.svg

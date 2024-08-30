Events
======

The ``http_client`` application dispatches a few events to interract with outbound HTTP requests and associated
responses.


HTTP Client Service Events
::::::::::::::::::::::::::

.. py:currentmodule:: harp_apps.http_client.events

Whenever an external HTTP request goes through the :service:`http_client` service to be sent out (assuming you're using
the default service implementation), the :class:`harp_apps.http_client.transport.AsyncFilterableTransport` transport
wrapper will dispach events to filter both :class:`httpx.Request` and :class:`httpx.Response` instances that represents
the HTTP request and response, respectively.

* :attr:`EVENT_FILTER_HTTP_CLIENT_REQUEST` is dispatched when an outbound HTTP request is about to be sent.

  It is dispatched with a :class:`HttpClientFilterEvent` instance.

  If a response is set on the event instance, then the actual outgoing request will be bypassed and the forged response
  will be returned.

* :attr:`EVENT_FILTER_HTTP_CLIENT_RESPONSE` is dispatched when an inbound HTTP response is received (either from the
  external service, or because it was forged).

  It is dispatched with the same :class:`HttpClientFilterEvent` instance as the previous event, with the response set.

  You can change the response instance on the event to modify the response that will be returned to the caller.

.. note::

    Please note that the same event instance will be used for both events. It means that if you stop propagation of the
    event, all further filtering will be skipped, for both events.

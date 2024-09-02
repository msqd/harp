HTTP Client Events
==================

.. tags:: events


The ``http_client`` application dispatches a few events to interract with outbound HTTP requests and associated
responses.


Filtering Events
::::::::::::::::

.. py:currentmodule:: harp_apps.http_client.events

Whenever an external HTTP request goes through the :service:`http_client` service to be sent out (assuming you're using
the default service implementation), the :class:`harp_apps.http_client.transport.AsyncFilterableTransport` transport
wrapper will dispach events to filter both :class:`httpx.Request` and :class:`httpx.Response` instances that represents
the HTTP request and response, respectively.


⚡️ EVENT_FILTER_HTTP_CLIENT_REQUEST
--------------------------------------

Dispatched when an outbound HTTP request is about to be sent.

It is dispatched as :attr:`EVENT_FILTER_HTTP_CLIENT_REQUEST` with a :class:`HttpClientFilterEvent` instance.

If a response is set on the event instance, then the actual outgoing request will be bypassed and the forged response
will be returned.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_FILTER_HTTP_CLIENT_REQUEST` event:

    .. literalinclude:: ./examples/events.filter.request.py


⚡️ EVENT_FILTER_HTTP_CLIENT_RESPONSE
---------------------------------------

Dispatched when an inbound HTTP response is received (either from the external service, or because it was forged).

It is dispatched as :attr:`EVENT_FILTER_HTTP_CLIENT_RESPONSE`, with the same :class:`HttpClientFilterEvent` instance as
the previous event, with the response set.

You can change the response instance on the event to modify the response that will be returned to the caller.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_FILTER_HTTP_CLIENT_RESPONSE` event:

    .. literalinclude:: ./examples/events.filter.response.py


Gotchas
-------

Those events are only dispatched if a request to an external service is ready to be sent. It will be bypassed if a
response has been forged before, or if the request hits the cache. If you're looking to filter incoming requests to the
proxy, have a look at :doc:`../proxy/events`.

Please note that the same event instance will be used for both events. It means that if you stop propagation of the
event, all further filtering will be skipped, for both events.

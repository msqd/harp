Proxy Events
============

.. tags:: events


The ``proxy`` application dispatches event arount the lifecycle of transactions and their associated messages (incoming
requests, outgoing responses, etc.).

Transaction Events
::::::::::::::::::

.. py:currentmodule:: harp_apps.proxy.events

The :class:`HttpProxyController <harp_apps.proxy.controllers.HttpProxyController>` is responsible for implementing the
actual proxy logic. It translates incoming requests into outgoing requests to remote services, and incoming responses
into outgoing responses to the caller (which, in fine, will be the user's http client).

This process is called a `Transaction` in HARP Proxy, and the controller provides events to interract with its
lifecycle.


⚡️ EVENT_TRANSACTION_STARTED
-----------------------------

Dispatched as a :attr:`EVENT_TRANSACTION_STARTED` event when a transaction object is created, with a
:class:`TransactionEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_TRANSACTION_STARTED` event:

    .. literalinclude:: ./examples/events.transaction.started.py


⚡️ EVENT_TRANSACTION_MESSAGE
-----------------------------

Dispatched as a :attr:`EVENT_TRANSACTION_MESSAGE` event when a message is sent to a transaction (either request or
response), with a :class:`HttpMessageEvent` instance.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_TRANSACTION_MESSAGE` event:

    .. literalinclude:: ./examples/events.transaction.message.py


⚡️ EVENT_TRANSACTION_ENDED
-----------------------

Dispatched as a :attr:`EVENT_TRANSACTION_ENDED` event, with a :class:`TransactionEvent` instance, when a transaction is
finished.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_TRANSACTION_ENDED` event:

    .. literalinclude:: ./examples/events.transaction.ended.py


Filtering Events
::::::::::::::::

To implement filtering logic (for rules, or your custom needs), a few events are here to let you filter the incoming
requests and their associated responses. You can even forge your own responses (maybe conditionnaly) to bypass the
proxying logic whenever needed.


⚡️ EVENT_FILTER_PROXY_REQUEST
--------------------------------

Dispatched when an incoming request is ready to be filtered, for example by the rules application.

Dispatched as a :attr:`EVENT_FILTER_PROXY_REQUEST` event, with a :class:`ProxyFilterEvent` instance.

If a response is set on the event instance, then the actual incoming request will be bypassed and the forged response
will be returned.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_FILTER_PROXY_REQUEST` event:

    .. literalinclude:: ./examples/events.filter.request.py


⚡️ EVENT_FILTER_PROXY_RESPONSE
---------------------------

Dispatched when an outgoing response is ready to be filtered, for example by the rules application.

Dispatched as a :attr:`EVENT_FILTER_PROXY_RESPONSE` event, with the same :class:`ProxyFilterEvent` instance as the
previous event, with the response set.

You can change the response instance on the event to modify the response that will be returned to the caller.

.. dropdown:: Example

    Here is an example of a listener coroutine for the :attr:`EVENT_FILTER_PROXY_RESPONSE` event:

    .. literalinclude:: ./examples/events.filter.response.py

Gotchas
-------

All incoming proxy requests will go through this event. If you're looking to filter outgoing HTTP requests, have a look
at :doc:`../http_client/events`.

Please note that the same event instance will be used for both events. It means that if you stop propagation of the
event, all further filtering will be skipped, for both events.

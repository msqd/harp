Events
======

The ``procy`` application dispatches event arount the lifecycle of transactions and their associated messages (incoming
requests, outgoing responses, etc.).

Proxy Events
::::::::::::

.. py:currentmodule:: harp_apps.proxy.events

The :class:`HttpProxyController <harp_apps.proxy.controllers.HttpProxyController>` is responsible for implementing the
actual proxy logic. It translates incoming requests into outgoing requests to remote services, and incoming responses
into outgoing responses to the caller (which, in fine, will be the user's http client).

This process is called a `Transaction` in HARP Proxy, and the controller provides events to interract with its
lifecycle.

* :attr:`EVENT_TRANSACTION_STARTED` is dispatched when a transaction is created.

  It is dispatched with a :class:`TransactionEvent` instance.

* :attr:`EVENT_TRANSACTION_MESSAGE` is dispatched when a message is sent to a transaction (either request or response).

  It is dispatched with a :class:`HttpMessageEvent` instance.

* :attr:`EVENT_TRANSACTION_ENDED` is dispatched when a transaction is finished, before the response is sent back to the
  caller.

  It is dispatched with a :class:`TransactionEvent` instance.

* :attr:`EVENT_FILTER_PROXY_REQUEST` is dispatched when an incoming request is ready to be filtered, for example by the
  rules application.

  It is dispatched with a :class:`ProxyFilterEvent` instance.

  If a response is set on the event instance, then the actual incoming request will be bypassed and the forged response
  will be returned.

* :attr:`EVENT_FILTER_PROXY_RESPONSE` is dispatched when an outgoing response is ready to be filtered, for example by
  the rules application.

  It is dispatched with the same :class:`ProxyFilterEvent` instance as the previous event, with the response set.

  You can change the response instance on the event to modify the response that will be returned to the caller.

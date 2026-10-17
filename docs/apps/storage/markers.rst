Transaction Markers
===================

.. versionadded:: 0.9

The storage application recognizes specific transaction markers that control how transaction data is persisted.
Markers can be added to transactions through the :doc:`rules application </apps/rules/index>` or programmatically
through the transaction API.

Vocabulary
::::::::::

One prefix per cause:

==============  ==============================================  ==========================================================
Prefix          Cause                                           Markers
==============  ==============================================  ==========================================================
``skip-``       A rule asked for it                             ``skip-storage``, ``skip-request-storage``,
                                                                ``skip-response-storage``, ``skip-request-body-storage``,
                                                                ``skip-response-body-storage``,
                                                                ``skip-request-headers-storage``,
                                                                ``skip-response-headers-storage``
``shed-``       Storage dropped data under pressure             ``shed-messages``, ``shed-headers``, ``shed-bodies``
``truncated-``  A recording cap cut the data                    ``truncated-response-body``
==============  ==============================================  ==========================================================

The storage worker sets the ``shed-`` markers when it drops the messages, headers or bodies of a transaction because
of its :attr:`pressure <harp_apps.storage.worker.StorageAsyncWorkerQueue.pressure>`. They tell an empty payload caused
by load shedding apart from one caused by a rule.

.. versionchanged:: 0.12
   Markers are persisted with the transaction (``markers`` column, comma separated) and returned by the transaction API.

Available Markers
:::::::::::::::::

Body Storage Markers
--------------------

``skip-request-body-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the request body to blob storage.
The request headers and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Large file uploads that you don't need to retain
- Requests containing sensitive data that should not be persisted
- Compliance requirements that prohibit storing certain request payloads

``skip-response-body-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the response body to blob storage.
The response headers and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Large file downloads that you don't need to retain
- Responses containing sensitive data that should not be persisted
- Compliance requirements that prohibit storing certain response payloads

Header Storage Markers
----------------------

``skip-request-headers-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the request headers to blob storage.
The request body and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Requests with sensitive authentication headers that should not be persisted
- Compliance requirements that prohibit storing certain request headers

``skip-response-headers-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the response headers to blob storage.
The response body and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Responses with sensitive headers that should not be persisted
- Compliance requirements that prohibit storing certain response headers

Truncation Markers
------------------

``truncated-response-body``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.12

Set by the proxy when a response body is longer than the recording cap (``proxy.max_recorded_body_size``, 1 MiB by
default). The stored body holds the first bytes of the response, up to the cap; the client received it whole. The
dashboard shows the truncation on the response. See :ref:`proxy-buffering-and-streaming`.

Message Storage Markers
-----------------------

``skip-request-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the entire request message
(including headers, body, and message metadata).

This is useful for:

- Completely omitting request storage for specific endpoints
- Privacy requirements that prohibit storing any request data

``skip-response-storage``
~~~~~~~~~~~~~~~~~~~~~~~~~~

When this marker is present on a transaction, the storage worker will **not** persist the entire response message
(including headers, body, and message metadata).

This is useful for:

- Completely omitting response storage for specific endpoints
- Privacy requirements that prohibit storing any response data

Transaction Storage Marker
---------------------------

``skip-storage``
~~~~~~~~~~~~~~~~

When this marker is present, the entire transaction (including all messages, headers, and bodies) will **not** be
persisted to storage.

This marker can be set manually in your rules to completely skip storage for specific transactions. It is also
automatically set by the storage worker when it detects high system pressure
(see :attr:`pressure <harp_apps.storage.worker.StorageAsyncWorkerQueue.pressure>` property).

Notes
:::::

- Markers are persisted with the transaction row, written when the transaction ends, even when data is skipped. A
  transaction marked ``skip-storage`` has no row, so its markers are not persisted
- Multiple markers can be combined on a single transaction
- Message-level markers (``skip-request-storage``, ``skip-response-storage``) take precedence over component markers
  (``skip-request-body-storage``, ``skip-request-headers-storage``, etc.)
- The ``skip-storage`` marker takes precedence over all other markers

See Also
::::::::

- :doc:`Rules application </apps/rules/index>` - for examples of how to set markers using rules

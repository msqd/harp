Transaction Markers
===================

.. versionadded:: 0.9

The storage application recognizes specific transaction markers that control how transaction data is persisted.
Markers can be added to transactions through the :doc:`rules application </apps/rules/index>` or programmatically
through the transaction API.

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

- Markers are stored as part of the transaction metadata even when data is skipped
- Multiple markers can be combined on a single transaction
- Message-level markers (``skip-request-storage``, ``skip-response-storage``) take precedence over component markers
  (``skip-request-body-storage``, ``skip-request-headers-storage``, etc.)
- The ``skip-storage`` marker takes precedence over all other markers

See Also
::::::::

- :doc:`Rules application </apps/rules/index>` - for examples of how to set markers using rules

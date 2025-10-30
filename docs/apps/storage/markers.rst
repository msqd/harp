Transaction Markers
===================

.. versionadded:: 0.9

The storage application recognizes specific transaction markers that control how transaction data is persisted.
Markers can be added to transactions through the :doc:`rules application </apps/rules/index>` or programmatically
through the transaction API.

Available Markers
:::::::::::::::::

``skip-request-body-storage``
------------------------------

When this marker is present on a transaction, the storage worker will **not** persist the request body to blob storage.
The request headers and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Large file uploads that you don't need to retain
- Requests containing sensitive data that should not be persisted
- Compliance requirements that prohibit storing certain request payloads

``skip-response-body-storage``
-------------------------------

When this marker is present on a transaction, the storage worker will **not** persist the response body to blob storage.
The response headers and message metadata (summary, timestamps, etc.) will still be stored normally.

This is useful for:

- Large file downloads that you don't need to retain
- Responses containing sensitive data that should not be persisted
- Compliance requirements that prohibit storing certain response payloads

``skip-storage``
----------------

When this marker is present, the entire transaction (including all messages, headers, and bodies) will **not** be
persisted to storage.

This marker can be set manually in your rules to completely skip storage for specific transactions. It is also
automatically set by the storage worker when it detects high system pressure
(see :attr:`pressure <harp_apps.storage.worker.StorageAsyncWorkerQueue.pressure>` property).

Notes
:::::

- Markers are stored as part of the transaction metadata even when bodies are skipped
- Multiple markers can be combined on a single transaction
- Headers are always stored unless the entire transaction is skipped (``skip-storage`` marker)

See Also
::::::::

- :doc:`Rules application </apps/rules/index>` - for examples of how to set markers using rules

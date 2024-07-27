Audit Log
=========

.. versionadded:: 0.5

The Audit log (or Audit Trail) is a core system of HARP that stores all transactions passing through the proxy
(HTTP requests and responses, whether or not forwarded to a remote backend) in a storage for future inspection.

.. figure:: ../user/images/transactions-details.png
    :class: screenshot

Turned on by default, it allows to see the transaction content on the HARP dashboard. Transactions are cleaned up by
the Janitor application after a configured delay (by default, 2 months).

Enabled by default, it allows viewing transaction content on the HARP dashboard. Transactions are cleaned up by the
:doc:`Janitor Application <../apps/janitor/index>` after a configured delay (default is 2 months).

It is implemented by two applications working together:

- In the :doc:`Proxy Application <../apps/proxy/index>`, the
  :class:`HttpProxyController <harp_apps.proxy.controllers.HttpProxyController>` dispatches transaction-related events.
- In the :doc:`Storage Application <../apps/storage/index>`, the
  :class:`StorageAsyncWorkerQueue <harp_apps.storage.worker.StorageAsyncWorkerQueue>` reacts to these events and
  attempts to store them asynchronously in a storage.

Occasionally, high network pressure may cause the background worker to skip storing transaction data to maintain the
system's ability to process requests.

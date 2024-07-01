Audit Log
=========

.. versionadded:: 0.5

The Audit log (or Audit Trail) is a core system of harp that allows to store all transactions going through the proxy
(HTTP requests and responses, whether or not forwarded to a remote backend) in a storage, for eventual future
inspection.

Turned on by default, it allows to see the transaction content on the HARP dashboard. Transactions are cleaned up by
the Janitor application after a configured delay (by default, 2 months).

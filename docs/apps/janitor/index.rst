Janitor
=======

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.janitor`` application runs a background worker to clean up the storage. It deletes all transactions
older than the retention period (60 days by default), and the orphan blobs.

An orphan is a blob referenced by no message and by no HTTP cache entry. Blobs written in the last 10 minutes are kept,
as the message or cache entry referencing them may not be committed yet. ``cache/meta`` blobs, the HTTP cache entries
themselves, are never deleted by the janitor: cache storage is reclaimed by the ``ttl`` of ``http_cache.storage``
(see :doc:`/apps/http_cache/settings`). Once an entry is expired or replaced, the janitor removes the header and body
blobs nothing references anymore. The ``storage_blobs_orphans`` metric counts the same orphans.

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.janitor>


Settings
::::::::

``period``
    Seconds between two sweeps. Positive integer, default ``600`` (10 minutes).

``old_after``
    Age in days after which transactions are deleted. Positive integer, default ``60``.

``enabled``
    Set to ``false`` to disable the janitor. Default ``true``.

Zero and negative values are rejected when the configuration loads.

.. code-block:: yaml

    janitor:
      period: 3600  # sweep every hour
      old_after: 14  # keep two weeks of transactions

See the :doc:`settings reference <settings>`.

Loading
:::::::

The ``janitor`` application is loaded by default when using the ``harp-proxy start`` command.

You can disable it (not recommended) with ``janitor.enabled: false``, or by passing it as an argument to the
``harp-proxy start`` command:

.. code-block:: bash

    harp-proxy start --disable janitor ...

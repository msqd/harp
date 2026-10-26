Janitor
=======

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.janitor`` application runs a background worker that schedules the periodic cleanups, the *sweeps*, that
applications declare. It knows none of them: it runs the declared sweeps that are due on every pass (every ``period``
seconds, or less often when a sweep declares a longer interval), one after the other, and measures each of them (runs,
failures, items, duration; ``janitor_sweep_*`` Prometheus metrics, labelled by sweep). A sweep that fails or exceeds its
time budget never stops the others.

The storage application declares three sweeps, described in :ref:`storage-sweeps`: ``storage.transactions`` (retention),
``storage.blobs.orphans`` and ``storage.metrics``.

If the janitor is disabled, declared sweeps do not run, and startup logs a warning naming them. To declare a sweep from
your own application, see :doc:`/contribute/sweeps`.

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.janitor>


Settings
::::::::

``period``
    Seconds between two sweeps. Positive integer, default ``600`` (10 minutes).

``old_after``
    Deprecated alias of ``storage.retention_days``: when set, it is used as the retention, with a deprecation warning.
    If ``storage.retention_days`` is set too, it wins and a warning says ``old_after`` is ignored.

``enabled``
    Set to ``false`` to disable the janitor. Default ``true``.

Zero and negative values are rejected when the configuration loads.

.. code-block:: yaml

    janitor:
      period: 3600  # sweep every hour


See the :doc:`settings reference <settings>`.

Loading
:::::::

The ``janitor`` application is loaded by default when using the ``harp-proxy server`` command.

You can disable it (not recommended) with ``janitor.enabled: false``, or by passing it as an argument to the
``harp-proxy server`` command:

.. code-block:: bash

    harp-proxy server --disable janitor ...

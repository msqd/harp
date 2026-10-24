Sentry
======

.. tags:: applications

The ``harp_apps.contrib.sentry`` application reports proxy errors and traces to `Sentry <https://sentry.io>`_ when a
``dsn`` is configured.

Install the ``sentry`` extra, the Docker images already include it:

.. code-block:: shell

    pip install harp-proxy[sentry]

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.contrib.sentry>


Secrets are kept out of events
::::::::::::::::::::::::::::::

Settings can carry secrets (a database password in ``storage.url``), whether they come from the command line, a
configuration file or an environment variable. Events sent to Sentry never include:

- the command line (``sys.argv``), so a ``--set storage.url=...`` argument is not reported;
- the local variables of the frames in a traceback, where a setting loaded from a file or the environment may be held.

Exception messages are still sent as they are: do not put secrets in them.

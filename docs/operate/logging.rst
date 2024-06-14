Logging
=======

For logging purposes, Harp uses the standard python `logging` module, with `structlog` on top of it.

Logs are organized in a hierarchical manner according to the python package structure. The root logger sets up global
configurations which can be modified for each package or subpackage. The configurations for a package are inherited by
all its subpackages.


Log levels
::::::::::

To adjust the logs verbosity, set a lower minimum level for one of the loggers. Available log levels are, from most
verbose to least, ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.

- :code:`LOGGING_HARP=...`: log level for ``harp.*`` and ``harp_app.*`` loggers [default: ``INFO``].
- :code:`LOGGING_HARP_EVENTS=...`: log level for ``harp.event_dispatcher_*`` loggers [default: ``WARNING``]. Allows to
  get debug information about the events happening (managed by :mod:`whistle`).
- :code:`LOGGING_HTTP=...`: log level for ``httpcore.*`` and ``httpx.*`` loggers [default: ``WARNING``].
- :code:`LOGGING_HYPERCORN_ACCESS=...`: log level for ``hypercorn.access`` logger [default: ``WARNING``].
- :code:`LOGGING_HYPERCORN_ERROR=...`: log level for ``hypercorn.error`` logger [default: ``INFO``].


Formatters
::::::::::

There are a few different logs formatters that you can use depending on your needs:

- :code:`plain` is the simplest formatter, using a simple console output without colors (no ansi codes).
- :code:`pretty` is the default formatter, using colors so that the logs are easier to read.
- :code:`json` will format each log line as a small json, making it easy to ingest in log processing systems.
- :code:`keyvalue` is another structured formatter, using key=value pairs.

To choose a formatter, set the `LOGGING_FORMAT` environment variable:

.. code-block:: bash

    export LOGGING_FORMAT=json harp start ...


Special cases
:::::::::::::

SQL logs (SQLAlchemy)
---------------------

To enable SQL logs, you should configure the sqlalchemy logger minimum level to ``INFO``

.. code-block:: shell

    export LOGGING_SQL=INFO harp start ...

This works for all execution contexts, including tests, etc.

HTTP Client logs (HTTPX)
------------------------

.. todo:: Document how to enable HTTPX logs and the low level logs.


Questions
:::::::::

Why can't I configure the logger in harm regular config files?
--------------------------------------------------------------

The logger is a special case that needs to be configured at the earliest possible time in the application lifecycle.
We may consider about pre-reading config files to configure the logger in the future, but this creates some complexity
that we do not want to consider, for now.


Why does the logger-related environment variables have a different prefix?
--------------------------------------------------------------------------

The reason is basically the same as for the config files: as all ``HARP_`` prefixed environment variables are used to
extend the regular harp configuration, we decided to use a different prefix for the logger-related variables to avoid
confusion or hacks to discriminate between regular config and logger-related config.

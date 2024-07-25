Logging
=======

Logging is a crucial part of any application. It helps developers understand what's happening inside their application
by recording events, errors, and other significant activities. HARP utilizes Python's built-in ``logging`` module,
enhanced with ``structlog`` for structured logging.

Logs are organized based on the Python package hierarchy. This means you can set up global logging configurations that
apply to the entire application, and then adjust settings for specific packages or components as needed. These settings
are inherited by any sub-packages, allowing for fine-grained control over log output.


Log Verbosity
:::::::::::::

Log verbosity determines how much detail is logged. HARP supports several log levels:

* ``DEBUG``: Logs detailed information, typically of interest only when diagnosing problems.
* ``INFO``: Logs general system information.
* ``WARNING``: Logs potential issues that should be addressed.
* ``ERROR``: Logs serious issues that have occurred.
* ``CRITICAL``: Logs very serious issues that might cause the application to stop running.

You can adjust the verbosity for different parts of HARP using environment variables:

* ``LOGGING_HARP``: Log level for HARP's core and applications.
* ``LOGGING_EVENTS``: Log level for internal event dispatching.
* ``LOGGING_HTTP_CLIENT``: Log level for HTTP client (httpcore and httpx) related logs.
* ``LOGGING_PROXY``: Log level for proxy related logs.
* ``LOGGING_HTTP``: Log level for HTTP server (hypercorn) related logs.
* ``LOGGING_SQL``: Log level for SQL related logs.


Choosing a Log Format
:::::::::::::::::::::

HARP supports multiple log formats to suit different needs:

* ``plain``: Simple text output without color.
* ``pretty``: Colorized output for easier reading.
* ``json``: Structured JSON output for integration with log processing systems.
* ``keyvalue``: Key-value pair output for structured logging.

Set the ``LOGGING_FORMAT`` environment variable to choose a format:

.. code-block:: bash

    LOGGING_FORMAT=json harp start ...


Questions
:::::::::

Why is logging configured via environment variables?
----------------------------------------------------

Logging needs to be set up early in the application's lifecycle, before most of the configuration is read. Using
environment variables allows for immediate application of log settings.


Why do logging environment variables use a different prefix?
------------------------------------------------------------

To avoid confusion with HARP's main configuration, logging settings use a different prefix. This ensures a clear
distinction between general application settings and logging-specific configurations.

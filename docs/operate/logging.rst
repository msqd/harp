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

Environment Variables
---------------------

You can adjust the verbosity for different parts of HARP using environment variables:

* ``LOGGING``: Root logger level (default: ``INFO``)
* ``LOGGING_HARP``: HARP core and applications (default: ``INFO``)
* ``LOGGING_EVENTS``: Internal event dispatching (default: ``WARNING``)
* ``LOGGING_HTTP_CACHE``: HTTP cache application (default: ``WARNING``)
* ``LOGGING_HTTP_CLIENT``: HTTP client application (default: ``WARNING``)
* ``LOGGING_HTTP_CORE``: Low-level HTTP libraries (httpcore, httpx) (default: ``WARNING``)
* ``LOGGING_PROXY``: Proxy application (default: ``WARNING``)
* ``LOGGING_STORAGE``: Storage application (default: ``WARNING``)
* ``LOGGING_HTTP``: HTTP server (hypercorn access/error logs) (default: ``INFO``)
* ``LOGGING_SQL``: SQLAlchemy engine logs (default: ``WARNING``)

Configured Loggers
------------------

The following loggers are pre-configured:

* ``harp`` - Core framework (controlled by ``LOGGING_HARP``)
* ``harp.event_dispatcher`` - Event system (controlled by ``LOGGING_EVENTS``)
* ``harp_apps`` - All applications (controlled by ``LOGGING_HARP``)
* ``harp_apps.http_cache`` - HTTP cache application (controlled by ``LOGGING_HTTP_CACHE``)
* ``harp_apps.http_client`` - HTTP client application (controlled by ``LOGGING_HTTP_CLIENT``)
* ``harp_apps.proxy`` - Proxy application (controlled by ``LOGGING_PROXY``)
* ``harp_apps.storage`` - Storage application (controlled by ``LOGGING_STORAGE``)
* ``httpcore`` - HTTP core library (controlled by ``LOGGING_HTTP_CORE``)
* ``httpx`` - HTTP client library (controlled by ``LOGGING_HTTP_CORE``)
* ``hypercorn.access`` - HTTP server access logs (controlled by ``LOGGING_HTTP``)
* ``hypercorn.error`` - HTTP server error logs (controlled by ``LOGGING_HTTP``)
* ``sqlalchemy.engine`` - Database engine logs (controlled by ``LOGGING_SQL``)


Choosing a Log Format
:::::::::::::::::::::

HARP supports multiple log formats to suit different needs:

* ``plain``: Simple text output without color.
* ``pretty``: Colorized output for easier reading (default).
* ``json``: Structured JSON output for integration with log processing systems.
* ``keyvalue``: Key-value pair output with timestamp, level, event, and logger fields.

Set the ``LOGGING_FORMAT`` environment variable to choose a format (defaults to ``pretty`` if unset or invalid):

.. code-block:: bash

    LOGGING_FORMAT=json harp-proxy start ...


Using Logging in Code
::::::::::::::::::::::

HARP provides a ``get_logger`` function to obtain loggers in your code:

.. code-block:: python

    from harp._logging import get_logger

    logger = get_logger(__name__)
    logger.info("message", key="value")

The ``get_logger`` function normalizes logger names by:

* Treating ``__init__``, ``__main__``, and ``__app__`` module names as package names
* Mapping ``env_py`` to ``__migrations__`` for Alembic migrations

Structured Logging Features
----------------------------

HARP uses ``structlog`` which provides:

* **Structured context**: Log key-value pairs alongside messages
* **Context variables**: Automatic inclusion of contextvars in logs
* **Timestamp**: ISO format timestamps on all log entries
* **Exception formatting**: Rich exception tracebacks with formatting adapted to terminal width
* **Logger name and level**: Automatically included in all log entries


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

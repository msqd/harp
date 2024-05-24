Logging
=======

Logging is done using the standard python `logging` module, with `structlog` on top of it.

For now, it can only be configured using the following environment variables:

.. code-block:: env

    LOGGING_HARP=DEBUG|INFO|WARNING|ERROR|CRITICAL              # default: INFO
    LOGGING_HTTPCORE=DEBUG|INFO|WARNING|ERROR|CRITICAL          # default: INFO
    LOGGING_HTTPX=DEBUG|INFO|WARNING|ERROR|CRITICAL             # default: WARNING
    LOGGING_HYPERCORN_ACCESS=DEBUG|INFO|WARNING|ERROR|CRITICAL  # default: WARNING
    LOGGING_HYPERCORN_ERROR=DEBUG|INFO|WARNING|ERROR|CRITICAL   # default: INFO

.. warning::

    This will change, to be more consistent with the rest of the settings, although it's probably not a good idea to
    merge the logging settings with the proxy settings, as it targets a different execution level. Probably
    `--logging-*` flags will be added. Not urgent.

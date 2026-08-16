Run
===

.. note::

    This document describes the options to run the application on your local machine. Although the topic is similar, if
    you're looking for a guide on how to deploy the application to a server, please refer to the
    :doc:`runtime section of the operator's guide <../operate/runtime>`.


Running HARP
::::::::::::

You can run HARP in several ways depending on your needs.

With configuration files
-------------------------

The simplest approach using ``uvx`` (no installation needed):

.. code:: shell

    uvx --python 3.13 harp-proxy server --file config.yml

With multiple configuration files:

.. code:: shell

    uvx --python 3.13 harp-proxy server --file config1.yml --file config2.yml

For configuration syntax and options, see :doc:`configuration guide </operate/configure/index>`.

With a project
--------------

If you've created a project using ``harp-proxy create project``, use the generated ``Makefile``:

.. code:: shell

    cd your-project
    make start

While developing, use ``make dev`` instead: it runs the same server with auto-reload, restarting it
whenever you change a file.

.. code:: shell

    cd your-project
    make dev

Or run directly with UV:

.. code:: shell

    uv run harp-proxy server --enable your_app

Combine project and configuration:

.. code:: shell

    uv run harp-proxy server --enable your_app --file config.yml


Project structure
:::::::::::::::::

A HARP project is a standard Python package with a dependency on ``harp-proxy``. The structure is minimal:

.. code:: text

    your-project/
    ├── pyproject.toml       # Python package metadata
    ├── Makefile             # Common development commands
    ├── config.yml           # (optional) Configuration file
    ├── your_app/            # (optional) Custom application
    │   ├── __init__.py
    │   └── __app__.py       # Application metadata
    └── tests/               # Test directory

Package management
------------------

We recommend **UV** for fast dependency resolution (``uv sync``, ``uv add package``), but you're free to use any Python package manager. For other options, see the `Python Packaging User Guide <https://packaging.python.org/en/latest/guides/tool-recommendations/>`_.

The only requirement is a dependency on ``harp-proxy`` in your ``pyproject.toml``.

Application metadata
--------------------

Custom HARP applications define their lifecycle in ``__app__.py``. Here's a minimal example (see ``harp_apps.acme/__app__.py`` for reference):

.. code:: python

    from harp.config import Application

    application = Application(
        on_bind=...,    # Called during dependency injection setup
        on_bound=...,   # Called after DI container is built
        on_ready=...,   # Called when server is ready
        on_shutdown=..., # Called during shutdown
    )

For detailed information on creating custom applications, see :doc:`/contribute/applications/index`.


Debugging & logging
:::::::::::::::::::

Logging
-------

Control log verbosity with environment variables. For example, to enable debug logging:

.. code:: shell

    # Enable debug logging for HARP core
    LOGGING_HARP=DEBUG uvx --python 3.13 harp-proxy server --file config.yml

For complete logging documentation, including all available log levels, formats, and configured loggers, see :doc:`/operate/logging`.


Common development workflows
:::::::::::::::::::::::::::::

Quick config testing
--------------------

.. code:: shell

    # Test a configuration quickly
    uvx --python 3.13 harp-proxy server --file config.yml

    # With debug logging
    LOGGING_HARP=DEBUG uvx --python 3.13 harp-proxy server --file config.yml

Development with custom code
-----------------------------

.. code:: shell

    cd your-project

    # Install dependencies
    make install

    # Run tests
    make test

    # Start with debug logging
    LOGGING_HARP=DEBUG make start

Adding dependencies
-------------------

With UV (recommended):

.. code:: shell

    uv add httpx  # Add a dependency
    uv add --dev pytest-cov  # Add a dev dependency

With other tools, edit ``pyproject.toml`` and run your package manager's install command.

Quick Start
===========

Install & Bootstrap
:::::::::::::::::::

To start developing with HARP (create your own proxies with custom code), you need a few
things:

**Install HARP to be used as a CLI/dev tool**

.. code:: shell

    pipx install 'harp-proxy[dev]'

.. note::

    This will install an isolated instance of HARP that we'll mostly use to create new
    projects. It is possible to do it without, but this is the easiest.

**Bootstrap a new project**

.. code:: shell

    harp create project

This command will:

- Prompt you for project details (name, author, etc.)
- Ask whether to create an application folder (for custom code)
- Ask whether to create a configuration file
- Generate a project structure with:

  - Modern ``pyproject.toml`` using PEP 621 standard
  - UV-based dependency management (no Poetry)
  - Ready-to-use ``Makefile`` with common targets
  - Python 3.13 compatibility

Answer a few questions, and you're ready to go!


**Start your project**

.. code:: shell

    cd <your-project>
    make

This will install the dependencies using ``uv sync`` (creating a virtual environment) and start your proxy.

The generated project uses UV for package management, providing fast dependency resolution and installation. Common commands in your new project:

.. code:: shell

    make install  # Install dependencies with uv sync
    make start    # Start the HARP server
    make test     # Run tests with pytest

Next Steps
::::::::::

Congratulations, you created your first HARP project! Now you can start tuning it.

.. todo:: pointers

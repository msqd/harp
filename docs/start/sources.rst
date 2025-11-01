Sources
=======

To install from sources, you'll need `git`, `uv` and `make` available.

.. note::
   **Python 3.13 Required**

   HARP 0.9+ requires Python 3.13. UV will automatically manage the correct Python version, but ensure UV itself is installed on your system.

Clone the repository, then in its directory run:

.. code-block:: bash

    make install-dev
    uv run harp-proxy server

The ``make install-dev`` command installs all development dependencies including frontend tooling (Node.js/pnpm) and sets up pre-commit hooks. The project's ``pyproject.toml`` specifies Python 3.13 as a requirement, and UV will use the correct version automatically.

.. note::
   **Docker Required for Tests**

   Running the full test suite requires Docker, as tests use testcontainers to spawn database instances (PostgreSQL, MySQL).

Development Workflow
::::::::::::::::::::

For detailed information on contributing, testing, and development workflow, see :doc:`/contribute/index`.

.. include:: _next_steps.rst

Sources
=======

To install from sources, you'll need `git`, `uv` and `make` available.

.. note::
   **Python 3.13 Required**

   HARP 0.9+ requires Python 3.13. UV will automatically manage the correct Python version, but ensure UV itself is installed on your system.

Sources are meant for development. Clone the repository, then follow :doc:`/contribute/setup`: it installs the
dependencies (backend, frontend, pre-commit hooks) and starts a development server with the dashboard on port 4080.

.. note::
   **Docker Required for Tests**

   Running the full test suite requires Docker, as tests use testcontainers to spawn database instances (PostgreSQL; MySQL is unsupported since 0.13 and no longer tested in CI).

Development Workflow
::::::::::::::::::::

For detailed information on contributing, testing, and development workflow, see :doc:`/contribute/index`.

.. include:: _next_steps.rst

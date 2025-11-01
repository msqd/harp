Sources
=======

To install from sources, you'll need `git`, `uv` and `make` available.

.. note::
   **Python 3.13 Required**

   HARP 0.9+ requires Python 3.13. UV will automatically manage the correct Python version, but ensure UV itself is installed on your system.

Clone the repository, then in its directory run:

.. code-block:: bash

    make install-dev
    uv run harp start

The project's ``pyproject.toml`` specifies Python 3.13 as a requirement, and UV will use the correct version automatically.

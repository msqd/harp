UV & UVX (Recommended)
======================

The fastest way to install and run HARP is using `UV <https://docs.astral.sh/uv/>`_, a fast Python package manager.

Install UV
::::::::::

Install UV on your system:

.. code-block:: shell

    # On macOS and Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

For other installation methods, see the `UV installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

Quick Start with UVX
::::::::::::::::::::

The fastest way to try HARP:

.. code-block:: shell

    # Run HARP directly
    uvx harp-proxy --help

    # Start a server with example configuration
    uvx harp-proxy server --example sqlite --example proxy:httpbin

This will start the proxy with SQLite storage and a httpbin endpoint. The dashboard will be available at http://localhost:4080.

Test Your Proxy
:::::::::::::::

Send some requests through your proxy:

.. code-block:: shell

    # Send requests through the proxy
    curl "http://localhost:4000/get"
    curl "http://localhost:4000/json"

    # View results in the dashboard
    open http://localhost:4080

Local Development
:::::::::::::::::

For development work, clone the repository and use UV:

.. code-block:: shell

    # Clone the repository
    git clone https://github.com/msqd/harp.git
    cd harp

    # Install dependencies
    uv sync

    # Run HARP
    uv run harp-proxy server --example sqlite --example proxy:httpbin

Common Commands
:::::::::::::::

.. code-block:: shell

    # One-time execution (no install needed)
    uvx harp-proxy server --help

    # Run from local project
    uv run harp-proxy server
    uv run python -m harp server

    # Install dependencies
    uv sync

Next Steps
::::::::::

Now that you have HARP running:

1. **Learn the basics:** :doc:`/develop/quick-start`
2. **Configure your proxy:** :doc:`/operate/configure/index`
3. **Explore features:** :doc:`/features/index`

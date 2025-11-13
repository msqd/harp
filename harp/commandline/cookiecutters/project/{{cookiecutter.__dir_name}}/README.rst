Example: {{cookiecutter.name}}
=========={{'=' * cookiecutter.name|length}}

Quick Start
-----------

.. code:: shell

	# Show all available commands
	make help

	# Install dependencies
	make install

	# Start the HARP proxy server
	make start

Available Commands
------------------

``make help``
    Display all available Makefile targets with descriptions.

``make install``
    Install project dependencies using UV. Add ``DEBUG=1`` to see verbose output:

    .. code:: shell

        DEBUG=1 make install

``make start``
    Start the HARP proxy server. Configure options via ``HARP_OPTIONS``:

    .. code:: shell

        # Start with custom dashboard port
        HARP_OPTIONS="--set dashboard.port=8080" make start

        # Start with SQLite example enabled
        HARP_OPTIONS="--example sqlite" make start

``make test``
    Run the test suite with pytest.

``make clean``
    Remove generated files (.venv, caches, build artifacts).

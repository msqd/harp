Containers
==========

Basics
::::::

To build containers:

.. code-block:: bash

    $ make build

This uses provided Dockerfile to build the default production ready container.

You can now run the container with:

.. code-block:: bash

    $ make run

Or of you prefer an interactive shell:

.. code-block:: bash

    $ make run-shell

Build recipe
::::::::::::

To work on the build recipe (aka the Dockerfile), it may be more convenient to stop the build at a given stage.

.. code-block:: bash

    $ docker build --progress=plain --target=<build stage> -t devproxy .

You can run the just built container with:

.. code-block:: bash

    $ docker run -it --network host --rm devproxy

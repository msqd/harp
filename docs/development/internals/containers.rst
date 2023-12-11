Containers
==========

To build containers, one runs the following command:

.. code-block:: bash

    $ make build

This uses provided Dockerfile to build the default production ready container.

To work on the Dockerfile, it may be more convenient to stop the build at a given stage.

.. code-block:: bash

    $ docker build --progress=plain --target=<build stage> -t devproxy .

You can run the just built container with:

.. code-block:: bash

    $ docker run -it --network host --rm devproxy

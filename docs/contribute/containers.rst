Containers
==========

HARP containers are built using standard Python images with the released wheel installed.

Building
::::::::

To build the runtime image locally:

.. code:: bash

    make buildc

Running
:::::::

To run a locally built container:

.. code:: bash

    make runc

Or to get a shell:

.. code:: bash

    make runc-shell

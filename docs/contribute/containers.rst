Containers
==========

A few recipes are available to build local containers for the harp, that can be used for development or testing
purposes. This is not intented to serve as a guide to building custom images (although a few things there may still
help).


Stages
::::::

We're using `docker's multi-stage builds <https://docs.docker.com/build/building/multi-stage/>`_ to keep the final image
as small and focused as possible.

.. graphviz::

   digraph stages {
      rankdir=LR;

      "library/python" -> base [label="extends"];
      base -> backend [label="extends"];
      base -> development [label="extends"];
      base -> frontend [label="extends"];
      "library/python" -> runtime [label="extends"];

      backend -> runtime [style="dashed", label="copy"];
      frontend -> runtime [style="dashed", label="copy"];
   }

- **base**: This is the base image for all the other stages. It contains the common dependencies and tools that are
  shared between the backend and frontend. It is based on the official Python image.
- **backend**: This stage is used to build the python environment and sources.
- **frontend**: This stage is used to build the frontend assets, aka compile typescript/css into a dependency-less
  frontend that can be served to a (modern) browser.
- **development**: This stage is used to build a development environment, that can be used to run all the test suites,
  documentation, etc... important stuff that we do not want in the final runtime image.
- **runtime**: This is the final image that will be used to run the harp. It is based on the official Python image and
  contains the strict minimum necessary for harp to run in real world environments.


Building
::::::::

To build the runtime image locally, you can:

.. code:: bash

    make buildc

To build the development image locally, you can:

.. code:: bash

    make buildc-dev

To build a named stage locally, you can:

.. code:: bash

    DOCKER_BUILD_TARGET=<stagename> make buildc


Running
:::::::

To run a locally built container, you can:

.. code:: bash

    make runc

Or, to get a shell...

.. code:: bash

    make runc-shell

You need to build the image first.

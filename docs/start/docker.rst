Docker & Docker Compose
=======================

A ready-to-use image is published on Docker Hub as
`makersquad/harp-proxy <https://hub.docker.com/repository/docker/makersquad/harp-proxy>`_.


Download the image
::::::::::::::::::

To download the latest stable version, use:

.. code-block:: shell

    docker image pull makersquad/harp-proxy

Published tags:

- ``X.Y.Z``, ``X.Y``, ``X`` and ``latest`` for stable releases (``latest`` is the most recent stable release).
- ``X.Y.Z-rcN`` (or any other pre-release suffix) for pre-releases, exact tag only.
- ``unstable`` for the latest commit of the ``main`` branch.
- ``X.Y-git`` for the latest commit of a version branch (e.g. ``0.11-git``).

The image runs as a non-root user (uid 1000) and expects ``docker run --init`` (a minimal init process, for proper
signal handling), which all the examples below use.


Start a proxy
:::::::::::::

For a test run, you can:

.. code-block:: shell

    docker run --init -it --rm -p 4000-4100:4000-4100 makersquad/harp-proxy server

This will start the proxy using the default settings (in memory sqlite storage) and by default, the dashboard will be
available at http://localhost:4080.

Without configured endpoints, no traffic can be proxied yet.

Stop this container and run another with a remote endpoint setup:

.. code-block:: shell

    docker run --init -it --rm -p 4000-4100:4000-4100 makersquad/harp-proxy server --endpoint httpbin=4000:http://httpbin.org

This will start a container with an additional port that will proxy requests to `httpbin.org <http://httpbin.org>`_.

.. include:: _test_your_proxy.rst


Adding a configuration file
:::::::::::::::::::::::::::

If you want to add a simple configuration file, you can mount it in the default system location using docker.

First, create a configuration file (see :doc:`/operate/configure/index` for all configuration options):

.. code-block:: shell

    cat > harp.yaml <<EOF
    proxy:
      endpoints:
        - name: httpbin
          url: http://httpbin.org
          port: 4000
    EOF

Then run the container again, binding it to ``/etc/harp.yaml``:

.. code:: shell

    docker run --init -it --rm -p 4000-4100:4000-4100 --volume $(pwd)/harp.yaml:/etc/harp.yaml makersquad/harp-proxy server


Use docker compose
::::::::::::::::::

To add a harp proxy to your `docker-compose.yml` file, first create a configuration file (see :doc:`/operate/configure/index` for all options):

.. code-block:: shell

    cat > harp.yaml <<EOF
    proxy:
      endpoints:
        - name: httpbin
          url: http://httpbin.org
          port: 4000
    storage:
      url: sqlite+aiosqlite:////data/harp.db
    EOF

Then add the following to your `docker-compose.yml` file:

.. code-block:: yaml

    services:
      harp:
        image: makersquad/harp-proxy
        command: server
        init: true
        volumes:
          - "./harp.yaml:/etc/harp.yaml"
          - "./harp-data:/data"
        ports:
          - 4000-4100:4000-4100

This example setup will bind two volumes: one for the local configuration file and one holding the SQLite database
(``storage.url`` in ``harp.yaml``). Without ``storage.url``, storage is in memory and nothing is written to the volume.
Create the ``harp-data`` directory before starting the container, owned by uid 1000 (the user inside the container),
otherwise the database cannot be created:

.. code-block:: shell

    mkdir harp-data && sudo chown 1000:1000 harp-data

Once you're ready, just start your service set:

.. code-block:: shell

    docker compose up

You'll be able to find the same setup as we previously described using docker by itself, but with the added benefit of
having a configuration file instead of passing all settings on the command line.

.. include:: _next_steps.rst

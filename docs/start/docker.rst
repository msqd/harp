Docker & Docker Compose
=======================

A ready-to-use image is published on Docker Hub as
`makersquad/harp-proxy <https://hub.docker.com/repository/docker/makersquad/harp-proxy>`_.


Download the image
::::::::::::::::::

To download the latest stable version, use:

.. code-block:: shell

    docker image pull makersquad/harp-proxy

Tags are available for all tagged versions, and for latest points of main and dev branches (`git-main` and `git-dev`
respectively).


Start a proxy
:::::::::::::

For a test run, you can:

.. code-block:: shell

    docker run -it --rm -p 4000-4100:4000-4100 makersquad/harp-proxy

This will start the proxy using the default settings (in memory sqlite storage) and by default, the dashboard will be
available `locally on the 4080 port <http://localhost:4080>`_.

This first run is not very interesting, because there are no proxy ports configured. Nothing can get through, yet.

Stop this container and run another with a remote endpoint setup:

.. code-block:: shell

    docker run -it --rm -p 4000-4100:4000-4100 makersquad/harp-proxy server --endpoint httpbin=4000:http://httpbin.org

This will start a container with an additional port that will proxy requests to `httpbin.org <http://httpbin.org>`_.

In another terminal, send a few requests through the configured proxy port (you can use your favorite http client for
this instead of curl):

.. code-block:: shell

    curl -X GET "http://localhost:4000/get" -H "accept: application/json"
    curl -X POST "http://localhost:4000/post" -H "accept: application/json"
    curl -X PUT "http://localhost:4000/put" -H "accept: application/json"

Open the `dashboard <http://localhost:4080>`_ again, you'll be able to see the transactions that went through.


Use docker compose
::::::::::::::::::

To add a harp proxy to your `docker-compose.yml` file, first create a configuration file:

.. code-block:: shell

    cat > harp.yaml <<EOF
    proxy:
      endpoints:
        - name: httpbin
          url: http://httpbin.org
          port: 4000
    EOF

Then add the following to your `docker-compose.yml` file:

.. code-block:: yaml

    version: '3'

    services:
      harp:
        image: makersquad/harp-proxy:git-dev
        volumes:
          - "./harp.yaml:/etc/harp.yaml"
          - "./harp-data:/var/lib/harp/data"
        ports:
          - 4000-4100:4000-4100

This example setup will bind two volumes: one for the local configuration file and one to store data locally. You must
create the `harp.yaml` file (empty will do) and the `harp-data` directory before starting the container, but you don't
*have* to bind those volumes if you don't want to.

Once you're ready, just start your service set:

.. code-block:: shell

    docker-compose up

You'll be able to find the same setup as we previously described using docker by itself, but with the added benefit of
having a configuration file (instead of passing all settings on command line (this is also possible using docker by
itself, but is out of this document scope for now).

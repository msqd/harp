Quick start
===========

Intro
:::::::

Harp runs as a sidecar proxy between your app and remote APIs to enhance their reliability, performances and security
while adding observability and lowering the amount of userland code you'll need to write for common non-business needs.

.. figure:: images/tldr.png
   :alt: Basic proxy setup from the quickstart tl;dr

The runtime mostly consists in the ASGI proxy, forwarding http requests back and forth to configured endpoints.
As a free candy, you get a dashboard to observe the requests going through the proxy. Of course, this dashboard can be
disabled.

Quick install
:::::::::::::

The easiest way to run it is to use our docker image, but choose the flavour that suits you most.

.. tab-set-code::

    .. code-block:: docker

        # TODO review needed (config format updated since written)
        $ docker run -d \
                     -p 4000:4000 \
                     -p 4080:4080 \
                     -e HARP_PROXY_ENDPOINT_4000_NAME=httpbin \
                     -e HARP_PROXY_ENDPOINT_4000_TARGET=https://httpbin.org/ \
                     makersquad/harp-proxy:latest

    .. code-block:: compose

        $ cat <<EOF > docker-compose.yml
        version: '3'

        services:
          api-proxy:
            image: ...
            volumes:
              - "./config.yaml:/etc/harp.yaml"
              - "./data:/var/lib/harp/data"
            ports:
              - 4000:4000
              - 4080:4080

        EOF

        $ docker compose up -d

.. note::

    Other installation options exist but are out of the scope of this quick start guide.

    You can read more about :doc:`installing with docker <../installation/docker>`, :doc:`installing with docker
    compose <../installation/docker-compose>`, :doc:`installing with pip <../installation/pip>`, :doc:`installing with
    helm <../installation/helm>` and :doc:`installing from sources <../installation/sources>`.

    Configuration can also be provided via a lot of different means: command line arguments, environment variables,
    configuration files, or a mix of those. To dive in, :doc:`read more about configuration options
    <../configuration/index>`.

First glance
::::::::::::

Once the container runs, it will serve two different ports from your local host:

- `localhost:4000 <http://localhost:4000/>`_ serves a proxy to httpbin.org (an example external api that we'll use as our first proxy
  target)
- `localhost:4080 <http://localhost:4080/>`_ serves a dashboard allowing to observe the network traffic going through the proxy. It is
  activated and unsecure by default but for production environments you can disable it or add authentication.

Open the dashboard and go to the «Transactions» tab. It should be empty.

Now make a few requests through the proxy:

.. code-block:: bash

    # todo review this
    $ curl http://localhost:4000
    $ curl http://localhost:4000
    $ curl http://localhost:4000

If you go back to the dashboard, you'll now see the transactions.

Congratulations, you just ran your first harp proxy.


.. todo::

    And now what?

Quick start
===========

The main goal of HARP is to be a nearline proxy to remote HTTP APIs, to enhance observability and reliability while
lowering development, operations and maintenance costs.

You can read more about the core HTTP proxy features in the :doc:`/features/http-proxy` section of the documentation.

By default, it respects HTTP cache headers and will speed up your API calls without further configuration. Of course,
a lot of APIs are non-standard or behave strangely, and one goal of HARP is to give you a toolkit for fixing those.

Most usually complex but must-have features can be configured using very few lines of code (most often one or less),
and you can extend the existing or write your own using Python or Cython (for incredible speed and efficience, if
it's a need).

Installation
::::::::::::

The easiest way to run it is to use our docker image. It is available on docker hub as `makersquad/harp-proxy
<https://hub.docker.com/repository/docker/makersquad/harp-proxy>`_.

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
      # Should we provide a basic yaml file?
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
    # The doc from all the installation methods don't exist yet, even the ones that exist.
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

Next steps
::::::::::

.. todo::

    And now what?

    * configure your endpoints
    * configure your dashboard: auth, ...
    * write an extension application

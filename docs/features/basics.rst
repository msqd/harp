Basics
======

The basic goal of HARP is to be a nearline proxy to remote HTTP APIs, to enhance observability and reliability while
lowering development and maintenance cost by offloading all usual needed features to the proxy (caching, auditing,
alerting, retrying...).

You can read more about the core HTTP proxy features in the :doc:`http-proxy` section of the documentation.

By default, it respects HTTP cache headers and will speed up your API calls without further configuration. Of course,
a lot of APIs are non-standard or bahve strangely, and one goal of HARP is to give you a toolkit for fixing those.

Most usually complex but must-have features can be configured using very few lines of code (most often one or less),
and you can extend the existing or write your own using Python or Cython (for incredible speed and efficience, if
it's a need).

Getting started
:::::::::::::::

You run it locally, and query the local server instead of the remote API.

The easiest way to get started is to run it through docker:

.. code-block:: bash

    docker run -it --rm -p 4000:4000 -p 4080:4080 -e HARP_ENDPOINT_URL=https://httpbin.org makersquad/harp-proxy

Then you can query the proxy and get the same result as the remote API:

.. code-block:: bash

    curl http://localhost:4000/get

Open http://localhost:4080/ in your favorite browser and have a look to the proxy dashboard. You can inspect all
transactions (http request-response pairs) that went through the proxy.

At his point you can already get a lot of value out of HARP, but you can also configure it to do (much) more.

Please note that this default configuration is suited for development and testing, but not for production. Read the
production guide to learn about recommended settings for a live environment.

Configuration
:::::::::::::

Most of basic HARP settings can be set using environment variables. For a more readable or advanced setup, you can
configure it using its python API and/or a configuration file (various formats available like JSON, YAML, TOML, INI, ...).

Here is a simple example of a bootstrap script that will do the exact same thing as the docker command above:

.. code-block:: python

    from harp import ProxyFactory

    proxy = ProxyFactory()
    proxy.add("https://httpbin.org", port=4000)

    if __name__ == "__main__":
        proxy.run()

To run it with docker, save it as `proxy.py` use the following command (from the directory where you saved the file):

.. code-block:: bash

    docker run -p 4000:4000 -p 4080:4080 -v "$(pwd)"/proxy.py:/etc/harp/entrypoint.py nginx

Other ways to run
:::::::::::::::::

Docker Compose
--------------

Local Python Interpreter
------------------------

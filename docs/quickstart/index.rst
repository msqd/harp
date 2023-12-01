Quick start
===========

TL;DR;
::::::

Harp will run as a proxy between your app and remote APIs. The easiest way to run it is to use our docker image.
Configuration can be provided via environment variables (the simplest amongst available options).

.. code-block:: bash

    docker run -d -p 4080:4080 -p 4000:4000 -e HARP_PROXY_ENDPOINT_4000_NAME=httpbin -e HARP_PROXY_ENDPOINT_4000_TARGET=https://httpbin.org/ makersquad/harp-proxy:latest

This will proxy your local 4000 port to httpbin.org. All requests going through the proxy will be visible in the
dashboard: open http://localhost:4080/ and go to the transactions tab.

.. figure:: images/tldr.png
   :alt: Basic proxy setup from the quickstart tl;dr

Once you have this running, you may want to consider switching httpbin for some of your favorite apis, and switching
the human for an application you work on.

Getting the traffic through the proxy should be as simple as switching your application's configured API endpoints.


Installation
::::::::::::

The simplest option is to use the docker image.

Configuration
:::::::::::::

Various options are available for configuration. All options can be combined together, elements higher in the following
list will override elements lower in the list (unless something is "locked", in which case the higher order
configuration will fail with an exception).

* Command line options
* Environment variables
* Configuration file(s) (toml, ini, yaml, json, xml, ...)
* Python source code (programmatic api)

.. todo:: This is the target, not yet true for everything.

.. todo:: Decide the inheritance rules between the various configuration options.

Runtime
:::::::

The runtime mostly consists in the ASGI proxy, forwarding http requests back and forth to configured endpoints.
As a free candy, you get a dashboard to observe the requests going through the proxy. Of course, this dashboard can be
disabled.

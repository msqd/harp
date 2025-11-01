Python & PIP
============

Harp is also installable using a Python package manager (most likely, `pip`).

Install with PIP
::::::::::::::::::

You need a working Python 3.13+ environment with the `pip` package manager (or another package manager of your choice).
To install it, run:

.. code-block:: shell

    pip install harp-proxy


Start a proxy
:::::::::::::

Then, you'll be able to start the server using:

.. code-block:: bash

    harp-proxy server

This will start the proxy using the default settings (in memory sqlite storage) and by default, the dashboard will be
available at http://localhost:4080.

Without configured endpoints, no traffic can be proxied yet. Stop this process and start a server with an endpoint:

.. code-block:: shell

    harp-proxy server --endpoint httpbin=4000:http://httpbin.org

This will start a new harp server with an additional port that will proxy requests to `httpbin.org <http://httpbin.org>`_.

.. include:: _test_your_proxy.rst

.. include:: _next_steps.rst

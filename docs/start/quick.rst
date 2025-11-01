Quick start
===========

The main goal of HARP is to be a nearline proxy to remote HTTP APIs, to enhance observability and reliability while
lowering development, operations and maintenance costs.

.. todo::

    You can read more about the core HTTP proxy features in the ... section of the documentation.

By default, HARP proxies respects HTTP headers (cache ...) and will speed up your API calls without further
configuration. Of course, a lot of APIs are non-standard or behave strangely, and one goal of HARP is to give you a
toolkit for fixing those.


Installation
::::::::::::

The **fastest** way to run HARP is using UV:

.. code-block:: shell

    uvx harp-proxy server --example sqlite --example proxy:httpbin

.. note::
   HARP 0.9+ requires Python 3.13. If your system's default Python version is older, use:

   .. code-block:: shell

       uvx -p 3.13 harp-proxy server --example sqlite --example proxy:httpbin

   UV will automatically download and manage the correct Python version for you.

Alternatively, use our Docker image:

.. code-block:: shell

    docker run -it --rm \
               -p 4000-4100:4000-4100 \
               makersquad/harp-proxy:latest \
               server --endpoint httpbin=4000:http://httpbin.org/

For more installation options:

- :doc:`installing with UV (recommended) <uv>`
- :doc:`installing with docker and docker compose <docker>`
- :doc:`installing from a python package <python>`
- :doc:`installing from sources <sources>`

.. todo:: add link to configuration section


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

    curl -X GET "http://localhost:4000/get" -H "accept: application/json"
    curl -X POST "http://localhost:4000/post" -H "accept: application/json"
    curl -X PUT "http://localhost:4000/put" -H "accept: application/json"

If you go back to the dashboard, you'll now see the transactions.

Congratulations, you just ran your first harp proxy.


Next steps
::::::::::

.. todo::

    And now what?

    * configure your endpoints
    * configure your dashboard: auth, ...
    * write an extension application

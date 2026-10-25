Quick start
===========

The main goal of HARP is to be a nearline proxy to remote HTTP APIs, to enhance observability and reliability while
lowering development, operations and maintenance costs.

By default, HARP respects HTTP caching headers and will speed up your API calls without further configuration. Of course, a lot of APIs are non-standard or behave strangely, and HARP provides a toolkit for handling those edge cases. Read more about :doc:`/features/index` and :doc:`/features/proxy`.


Installation
::::::::::::

The **fastest** way to run HARP is using UV:

.. code-block:: shell

    uvx -p 3.13 harp-proxy server --endpoint httpbin=4000:http://httpbin.org

HARP requires Python 3.13: ``-p 3.13`` makes UV download and use it if your system has another one.

Alternatively, use our Docker image:

.. code-block:: shell

    docker run --init -it --rm \
               -p 4000-4100:4000-4100 \
               makersquad/harp-proxy:latest \
               server --endpoint httpbin=4000:http://httpbin.org/

For more installation options:

- :doc:`installing with UV (recommended) <uv>`
- :doc:`installing with docker and docker compose <docker>`
- :doc:`installing from a python package <python>`
- :doc:`installing from sources <sources>`

See :doc:`/operate/configure/index` for configuration options.


First glance
::::::::::::

Once HARP runs, it will serve two different ports from your local host:

- `localhost:4000 <http://localhost:4000/>`_ serves a proxy to httpbin.org (an example external api that we'll use as our first proxy
  target)
- `localhost:4080 <http://localhost:4080/>`_ serves a dashboard allowing to observe the network traffic going through the proxy. It is
  activated by default and requires a login: the ``admin`` password is generated at each start and printed in the logs
  (see :doc:`docker`), or you can :doc:`set your own </apps/dashboard/index>`.

Open the dashboard and go to the «Transactions» tab. It should be empty. The :doc:`user guide </user/transactions>` explains how to read it.

Now make a few requests through the proxy:

.. code-block:: bash

    curl -X GET "http://localhost:4000/get" -H "accept: application/json"
    curl -X POST "http://localhost:4000/post" -H "accept: application/json"
    curl -X PUT "http://localhost:4000/put" -H "accept: application/json"

If you go back to the dashboard, you'll now see the transactions.

Congratulations, you just ran your first harp proxy!

.. include:: _next_steps.rst

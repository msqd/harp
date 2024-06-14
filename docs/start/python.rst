Python & PIP
============

Harp is also installable using a Python package manager (most likely, `pip``).

Install with PIP
::::::::::::::::::

You need a working Python 3.12 environment with the `pip` package manager (or another package manager of your choice).
To insall it, run:

.. code-block:: shell

    pip install harp-proxy


Start a proxy
:::::::::::::

Then, you'll be able to start the server using:

.. code-block:: bash

    harp server

This will start the proxy using the default settings (in memory sqlite storage) and by default, the dashboard will be
available `locally on the 4080 port <http://localhost:4080>`_.
This first run is not very interesting, because there are no proxy ports configured. Nothing can get through, yet.
Stop this process and run another harp server with the following command:


.. code-block:: shell

    harp server --endpoint httpbin=4000:http://httpbin.org

This will start a new harp server with an additional port that will proxy requests to `httpbin.org <http://httpbin.org>`_.
In another terminal, send a few requests through the configured proxy port (you can use your favorite http client for
this instead of curl):

.. code-block:: shell

    curl -X GET "http://localhost:4000/get" -H "accept: application/json"
    curl -X POST "http://localhost:4000/post" -H "accept: application/json"
    curl -X PUT "http://localhost:4000/put" -H "accept: application/json"


Open the `dashboard <http://localhost:4080>`_ again, you'll be able to see the transactions that went through.

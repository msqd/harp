Send some requests through the configured proxy port:

.. code-block:: shell

    curl -X GET "http://localhost:4000/get" -H "accept: application/json"
    curl -X POST "http://localhost:4000/post" -H "accept: application/json"
    curl -X PUT "http://localhost:4000/put" -H "accept: application/json"

Open the dashboard at http://localhost:4080 to see the transactions that went through.

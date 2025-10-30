Recipes
=======

Cache
:::::

Force some (sub) endpoints to cache the response for a given time
-----------------------------------------------------------------

.. code-block:: yaml

    rules:
        "my-endpoint":
            "GET /foo/bar":
                on_remote_response:
                    response.headers['Cache-Control'] = 'max-age=3600'


Storage Control
:::::::::::::::

Skip storing request/response bodies
-------------------------------------

Use these markers to skip storing message bodies while keeping headers and metadata.
Useful for large file uploads/downloads or sensitive payloads.

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /upload":
          on_request: |
            transaction.markers.add("skip-request-body-storage")
        "GET /download":
          on_response: |
            transaction.markers.add("skip-response-body-storage")

Skip storing request/response headers
--------------------------------------

Use these markers to skip storing headers while keeping bodies and metadata.
Useful when headers contain sensitive authentication tokens or API keys.

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /api/*":
          on_request: |
            # Don't store authorization headers
            transaction.markers.add("skip-request-headers-storage")

Skip entire request or response messages
-----------------------------------------

Use these markers to completely omit storing requests or responses.
No headers, no body, no message metadata will be stored.

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /internal/*":
          on_request: |
            # Don't store anything about internal requests
            transaction.markers.add("skip-request-storage")
        "GET /health":
          on_response: |
            # Don't store health check responses
            transaction.markers.add("skip-response-storage")

Combining storage markers
--------------------------

Markers can be combined for fine-grained control:

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /api/upload":
          on_request: |
            # Skip both request body and headers
            transaction.markers.add("skip-request-body-storage")
            transaction.markers.add("skip-request-headers-storage")
          on_response: |
            # Only store response headers, skip body
            transaction.markers.add("skip-response-body-storage")

See the :doc:`storage markers documentation </apps/storage/markers>` for a complete reference.

Complete working example
------------------------

A comprehensive example demonstrating all storage markers is available as ``rules:storage-markers``.
This example includes basic usage of all marker types, conditional marker application based on
request/response properties, and combining multiple markers for fine-grained control.

You can run it with:

.. code-block:: bash

    harp-proxy start --example rules:storage-markers

.. collapse:: View complete example source

    .. literalinclude:: ../../../harp_apps/rules/examples/storage-markers.toml
       :language: toml

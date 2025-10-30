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


Disable the storing of body for requests
-----------------------------------------------------------------

There are two markers (`skip-request-body-storage` and `skip-response-body-storage`) that
allow disabling the storage of request/response bodies. They are used respectively for the Request part (body sent upstream)
and the Response part (response body from upstream).

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /upload":
          on_request: |
            transaction.markers.add("skip-request-body-storage")
          on_response: |
            transaction.markers.add("skip-response-body-storage")

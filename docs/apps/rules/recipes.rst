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


Disable the storing of payload for requests
-----------------------------------------------------------------

There are two markers (`skip-request-payload-storage` and `skip-response-payload-storage`) that
allows to disable the storing of payload. They are used respectively for the Request part (payload sent upstream)
and the Response part (response from upstream).

.. code-block:: yaml

    rules:
      "my-endpoint":
        "POST /upload":
          on_request: |
            transaction.markers.add("skip-request-payload-storage")
          on_response: |
            transaction.markers.add("skip-response-payload-storage")

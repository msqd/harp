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

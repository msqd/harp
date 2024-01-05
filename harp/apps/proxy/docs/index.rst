Proxy
=====

The `harp.apps.proxy` application implements the core harp proxy features.

Configuration
:::::::::::::

.. code-block:: yaml

    proxy:
        endpoints:
            - name: starwars
              port: 1234
              url: https://swapi.dev/

Proxy endpoints are the remote APIs that your proxy will serve. Each endpoint have a local port, a name, and a base URL.

.. warning::

    For now, endpoints does not support subpaths on remote side. For exemple: http://example.com/ is supported as
    an endpoint base url but not http://example.com/foo/bar. Proxy will still forward requests to sub paths but no
    rewriting will be done on the request path.

.. tab-set-code::

    .. code-block:: shell

        $ harp start --set proxy.endpoints.4000.name=httpbin \
                     --set proxy.endpoints.4000.url=http://httpbin.org

    .. code-block:: env

        $ export HARP__PROXY__ENDPOINTS__4000__NAME=httpbin
        $ export HARP__PROXY__ENDPOINTS__4000__URL=http://httpbin.org
        $ harp start

    .. code-block:: yaml

        proxy:
          endpoints:
            4000:
              name: httpbin
              url: http://httpbin.org

    .. code-block:: python

        from harp import HarpFactory
        proxy = ProxyFactory(
            settings={
                "proxy": {
                    "endpoints": {
                        "4000": {
                            "name": "httpbin",
                            "url": "http://httpbin.org"
                        }
                    }
                }
            },
            args=sys.argv[1:],
        )

    .. code-block:: helm

        endpoints:
          - name: httpbin
            port: "8080"
            url: https://httpbin.org/

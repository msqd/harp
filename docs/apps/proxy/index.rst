Proxy
=====

The `harp_apps.proxy` application implements the core harp proxy features.

Loading
:::::::

The proxy application is loaded by default when using the `harp start` command.


Configuration
:::::::::::::

.. literalinclude:: ./examples/swapi.yml
    :language: yaml

Proxy endpoints are the remote APIs that your proxy will serve. Each endpoint have a local port, a name, and a base URL.

Internal implementation: :class:`ProxySettings <harp_apps.proxy.settings.ProxySettings>`,
:class:`ProxyEndpointSetting <harp_apps.proxy.settings.ProxyEndpointSetting>`


.. warning::

    For now, endpoints does not support subpaths on remote side. For exemple: http://example.com/ is supported as
    an endpoint base url but not http://example.com/foo/bar. Proxy will still forward requests to sub paths but no
    rewriting will be done on the request path.

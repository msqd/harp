Proxy
=====

The `harp_apps.proxy` application implements the core harp proxy features, and includes the configuration logic for
endpoints.

Setup
:::::

The proxy application is loaded by default when using ``harp start ...`` or ``harp server ...`` commands.


Configuration
:::::::::::::

To configure proxy endpoints, you can use a yaml configuration file:

.. literalinclude:: ./examples/swapi.yml
    :language: yaml

Proxy endpoints are the remote APIs that your proxy will serve. Each endpoint have a local port, a name, and a base URL.

Internal implementation: :class:`ProxySettings <harp_apps.proxy.settings.ProxySettings>`,
:class:`ProxyEndpointSetting <harp_apps.proxy.settings.ProxyEndpointSetting>`


Command line
::::::::::::

It is also possible to add endpoints using the command line:

.. code-block:: bash

    harp start --endpoint starwars=1234:https://swapi.dev/

You can use multiple ``--endpoint ...`` arguments and the option is available for all server-like commands
(``harp start ...``, ``harp server ...``, ...).


.. warning::

    For now, endpoints does not support subpaths on remote side. For exemple: http://example.com/ is supported as
    an endpoint base url but not http://example.com/foo/bar. Proxy will still forward requests to sub paths but no
    rewriting will be done on the request path.

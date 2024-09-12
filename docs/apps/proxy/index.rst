Proxy
=====

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.proxy`` application provides the core proxy features for HARP and includes the configuration logic for
endpoints.

.. toctree::
    :hidden:
    :maxdepth: 1

    Events <events>
    Settings <settings>
    Internals </reference/apps/harp_apps.proxy>


Setup
:::::

The proxy application is enabled by default when using the harp start ... or harp server ... commands.

You can disable it with the --disable proxy option, although this is generally not recommended.


Configuration
:::::::::::::

Shorthand syntax example:

.. literalinclude:: ./examples/full-shorthand.yml
    :language: yaml

Full example:

.. literalinclude:: ./examples/full.yml
    :language: yaml

**Reference**

* :class:`proxy (ProxySettings) <harp_apps.proxy.settings.ProxySettings>`
* :class:`proxy.endpoints[] (ProxyEndpoint) <harp_apps.proxy.settings.ProxyEndpoint>`
* :class:`proxy.endpoints[].remote (HttpRemote) <harp_apps.proxy.models.remotes.HttpRemote>`
* :class:`proxy.endpoints[].remote.endpoints[] (HttpEndpoint) <harp_apps.proxy.models.remotes.HttpEndpoint>`
* :class:`proxy.endpoints[].remote.probe (HttpProbe) <harp_apps.proxy.models.remotes.HttpProbe>`


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

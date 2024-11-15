Proxy
=====

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.proxy`` application provides the core proxy features for HARP and includes the configuration logic for
endpoints (the mapping between local ports and remote urls, including how to handle them).

.. toctree::
    :hidden:
    :maxdepth: 1

    Events <events>
    Settings <settings>
    Internals </reference/apps/harp_apps.proxy>


Setup
:::::

The proxy application is enabled by default when using the harp start ... or harp server ... commands. You can disable
it with the --disable proxy option, although this will most probably result in an useless system.


Configuration
:::::::::::::

Minimal example
---------------

.. literalinclude:: ./examples/full-shorthand.yml
    :language: yaml

.. note::

    The url provided can be either a base url like ``https://api1.example.com/`` or a full url like ``https://api1.example.com/foo/bar/``.


.. seealso::

    :doc:`📃 Proxy Configuration Reference <settings>`



Full example
------------

.. literalinclude:: ./examples/full.yml
    :language: yaml

.. seealso::

    :doc:`📃 Proxy Configuration Reference <settings>`

Custom Controller
-----------------
You can also provide a custom controller to handle the proxy logic. This is useful if you want to add custom logic to
the proxy.
A custom controller must be defined as a :class:`Service <harp.config.configurables.Service>`.

.. literalinclude:: ./examples/custom_controller.yml
    :language: yaml

Command line
::::::::::::

It is also possible to add endpoints using the command line. This is available for quick tests but should not be used as
a permanent solution.

.. code-block:: bash

    harp start --endpoint starwars=1234:https://swapi.dev/

.. warning::

    The current CLI syntax is hackish and limited, the syntax will most probably change in the future.

You can use multiple ``--endpoint ...`` arguments and the option is available for all server-like commands
(``harp start ...``, ``harp server ...``, ...).

.. warning::

    For now, endpoints does not support subpaths on remote side. For exemple: http://example.com/ is supported as
    an endpoint base url but not http://example.com/foo/bar. Proxy will still forward requests to sub paths but no
    rewriting will be done on the request path.

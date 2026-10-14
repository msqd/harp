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

The proxy application is enabled by default when using the harp-proxy start ... or harp-proxy server ... commands. You can disable
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

    harp-proxy start --endpoint starwars=1234:https://swapi.dev/

.. warning::

    The current CLI syntax is hackish and limited, the syntax will most probably change in the future.

You can use multiple ``--endpoint ...`` arguments and the option is available for all server-like commands
(``harp-proxy start ...``, ``harp-proxy server ...``, ...).

Remote urls carrying a path
:::::::::::::::::::::::::::

An endpoint url may carry a path of its own, which is how you expose one subtree of an upstream
rather than the whole of it. The url acts as the base that an incoming request path is resolved
against, in the ordinary URL sense, so **end it with a slash if you mean it as a prefix**:

.. list-table::
    :header-rows: 1

    * - Endpoint url
      - Request
      - Forwarded to
    * - ``http://example.com``
      - ``/a/b``
      - ``http://example.com/a/b``
    * - ``http://example.com/api/v1/``
      - ``/a/b``
      - ``http://example.com/api/v1/a/b``
    * - ``http://example.com/api/v1``
      - ``/a/b``
      - ``http://example.com/api/a/b``

The last row is why the trailing slash matters: without it, the final segment is treated as a
resource rather than a directory and is replaced, exactly as a relative link on a web page would be.

Path guard
----------

A request may not leave the subtree the endpoint url points at. The proxy appends the request path to
that base path as received, and checks the result the way an upstream that decodes once would read
it: ``%2e`` as ``.``, ``%2f`` and ``\`` as ``/``, empty and ``.`` segments ignored, ``..`` going one
level up. These requests get ``400 Bad Request`` and nothing is sent upstream:

- a path that goes above the base path, even if it comes back: on ``http://example.com/api/v1/``,
  ``/../../admin``, ``/%2e%2e/admin``, ``/..%2fadmin`` and ``/../v1/b`` are all refused;
- a path holding a space or control byte (``0x00`` to ``0x20``, ``0x7f``). HTTP/1.1 servers refuse them
  already, HTTP/2 lets them through. ``%20`` is fine.

Dot segments that stay inside it are forwarded normally, so ``/a/b/../c`` reaches ``/a/c`` as expected,
and encoded characters inside a segment (``/user%3A42``, ``/a%2fb``) are forwarded unchanged.

Not covered yet (`#1009 <https://github.com/msqd/harp/issues/1009>`_):``..;`` segments, double encoding (``%252e``) and overlong UTF-8. If
your upstream reads any of those as a dot segment, do not rely on the base path alone to restrict
access.

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
that base path as received, byte for byte, and refuses anything an upstream or the http client could
resolve out of it. These requests get ``400 Bad Request`` and nothing is sent upstream:

- a path with a dot segment, ``.`` or ``..``, wherever it would resolve: ``/a/b/../c`` is refused as
  much as ``/../../admin``. A separator may be ``/``, ``\``, ``%2f`` or ``%5c``, and a dot ``.`` or
  ``%2e``, in any case and any mix, so ``/%2e%2e/admin``, ``/..%2fadmin`` and ``/a%2fb/../..`` are
  refused too;
- a path holding a space or control byte (``0x00`` to ``0x20``, ``0x7f``). HTTP/1.1 servers refuse them
  already, HTTP/2 lets them through. ``%20`` is fine;
- a path the proxy cannot parse, such as ``//[x/``.

Ordinary traffic is unaffected: browsers and HTTP clients resolve dot segments before sending, so
``curl http://harp/a/b/../c`` goes out as ``/a/c`` and is forwarded. Only a client sending the dot
segment as is (``curl --path-as-is``) gets the 400. Dots inside a segment are no dot segment:
``/.well-known/x``, ``/v1.2/x`` and ``/users/a%2eb`` are forwarded unchanged, like other encoded
characters (``/user%3A42``, ``/a%2fb``).

Not covered yet (`#1009 <https://github.com/msqd/harp/issues/1009>`_): ``..;`` segments, double
encoding (``%252e``), overlong UTF-8, a dot segment followed by an encoded NUL (``/%2e%2e%00/x``) and
Unicode look-alike dots (fullwidth ``．`` U+FF0E, sent as ``%EF%BC%8E``). Each escapes only on an
upstream that reads it as a dot segment (one that treats ``..;`` as ``..``, decodes twice, accepts
overlong UTF-8, truncates at NUL, or applies Unicode normalisation before resolving dot segments). If
your upstream does, do not rely on the base path alone to restrict access.

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

The proxy application is enabled by default when using the harp-proxy server ... command. You can disable
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

    harp-proxy server --endpoint starwars=1234:https://swapi.dev/

.. warning::

    The current CLI syntax is hackish and limited, the syntax will most probably change in the future.

You can use multiple ``--endpoint ...`` arguments and the option is available for all server-like commands
(``harp-proxy server ...``, ...).

.. _proxy-client-tags:

Client tags
:::::::::::

.. versionchanged:: 0.13

    Client tags are bounded.

A request header starting with ``x-harp-`` is removed from the request and stored as a tag on the transaction:
``x-harp-team: billing`` tags the transaction ``team=billing``. Clients need no authentication to set them, so tags are
bounded, and a tag over a bound is dropped while the request is proxied as usual:

- 20 tags per transaction (``max_count``): the first ones in request header order are kept;
- names up to 64 characters (``max_name_length``), values up to 255 (``max_value_length``). Oversized tags are dropped
  first and do not count towards the 20. These are the widths of the storage columns: the bounds can be lowered but
  not raised, and a configuration above them is rejected at startup.

Dropped tags are logged at debug level with the transaction id, never their value.

.. code-block:: yaml

    proxy:
      tags:
        max_count: 20
        max_name_length: 64
        max_value_length: 255

Tagging stays open: any name is accepted. If HARP is exposed to untrusted callers, strip ``x-harp-*`` headers from the
requests you do not trust (at your load balancer or gateway), or lower these bounds, since every kept tag is stored.

.. _proxy-forwarding-headers:

Forwarding headers and trusted proxies
::::::::::::::::::::::::::::::::::::::

.. versionchanged:: 0.13

    The peer address is sent upstream, and inbound forwarding headers are stripped unless the peer is trusted.

HARP tells the upstream who is calling it. On every proxied request it appends the address of the peer it is talking to
to ``X-Forwarded-For`` and to ``Forwarded`` (RFC 7239, ``for=``; an IPv6 address is bracketed and quoted:
``for="[2001:db8::1]"``). This applies to the request sent upstream only, never to the request recorded in the
dashboard.

The ``X-Forwarded-For``, ``Forwarded`` and ``X-Real-IP`` headers a client sends are claims it chose freely, so by default
they are stripped before the request goes upstream, and the upstream only sees the real peer. If HARP runs behind a load
balancer or gateway of yours, list its addresses in ``trusted_proxies``: what a trusted peer sends is kept, and the peer
is appended after it, so the upstream sees the whole chain.

.. code-block:: yaml

    proxy:
      trusted_proxies:
        - 10.0.0.0/8
        - fd00::/8

``trusted_proxies`` is a list of CIDR ranges (a single address works too) and is empty by default. Only list proxies you
operate: anything in these ranges can set the client address your upstream sees.

An IPv4-mapped peer (``::ffff:127.0.0.1``, as a dual-stack listener sees IPv4 clients) is read as plain IPv4:
``127.0.0.0/8`` trusts it, and the upstream sees ``127.0.0.1``. The reverse no longer holds: a range written in mapped
form (``::ffff:10.0.0.0/104``, ``::ffff:0:0/96``) or ``::/0`` does not match IPv4 peers any more. Write the IPv4 form
instead.

.. _proxy-buffering-and-streaming:

Buffering and streaming
:::::::::::::::::::::::

.. versionchanged:: 0.12

    Response bodies are streamed to the client, and recorded up to a cap.

**Responses are streamed.** The proxy passes the upstream's response body on to the client as it arrives, whether the
upstream sent a ``Content-Length`` or a chunked body, with or without the http cache. The client gets the first bytes
as soon as the upstream sends them, not once the upstream has finished.

**What HARP records is capped.** The transaction keeps at most the first ``max_recorded_body_size`` bytes of a response
body, 1 MiB by default, and that is all of the body the proxy holds in memory. A longer body is still sent whole to
the client, and:

- the recorded body is cut at the cap, and the transaction carries the ``truncated-response-body``
  :doc:`marker </apps/storage/markers>`, which the dashboard shows on the response;
- the response is not stored in the :doc:`http cache </apps/http_cache/index>`, which would otherwise have to hold all
  of it.

The same cap applies to request bodies: a longer one is forwarded whole to the upstream, recorded cut at the cap, and
the transaction carries the ``truncated-request-body`` marker.

.. code-block:: yaml

    proxy:
      # a byte count, or a size with its unit: 512KiB, 1MiB, 10MB
      max_recorded_body_size: 4MiB

.. _proxy-client-read-timeout:

**A silent client is cut.** A client that stops sending in the middle of a request body is answered ``408`` and
disconnected after ``client_read_timeout`` seconds (30 by default), and its request is never forwarded upstream, so
stalled clients cannot hold every connection. Each silence is timed on its own: a client that keeps sending, however
slowly, at shorter intervals is not cut. The timeout concerns the request only: a response streaming for longer, to a
client that sends nothing meanwhile, is not cut. A client that keeps sending too slowly is handled below.

.. code-block:: yaml

    proxy:
      client_read_timeout: 30.0

**A slow upload is cut.** A client must send its request body at ``min_request_body_rate`` bytes per second on average
(1 KiB/s by default), once ``request_body_grace_period`` seconds (10 by default) have elapsed. A slower one, such as a
client sending a byte every few seconds, is answered ``408`` and disconnected, and its request is never forwarded
upstream. A normal slow upload above the rate completes, however long it takes. Set ``min_request_body_rate`` to ``0``
to disable the check. The silence timeout above does not catch such a client, since it keeps sending.

.. code-block:: yaml

    proxy:
      min_request_body_rate: 1KiB
      request_body_grace_period: 10.0

.. _proxy-max-request-body-size:

**An oversized request can be refused.** There is no limit on the request body size by default. Set
``max_request_body_size`` and a request body larger than it is answered ``413``, and its request is never forwarded
upstream. A declared ``Content-Length`` above the cap is refused before any of the body is read; a chunked body is
refused as soon as it crosses the cap. Without a cap, the proxy holds the whole body in memory, so set one when HARP is
exposed to untrusted clients. An endpoint may set its own cap, in place of the global one.

.. code-block:: yaml

    proxy:
      max_request_body_size: 100MiB
      endpoints:
        - name: uploads
          url: http://uploads:8080
          max_request_body_size: 1GiB

The transaction ends once the body has been sent, so its duration, and the :doc:`TPDEX </user/performances>`
computed from it, cover the whole exchange including the transfer to the client. When the client goes away before the
end of the body, HARP stops reading the upstream and releases its connection at once, and the transaction is recorded
with the body read until then and the ``client-disconnected`` marker. When
the upstream fails halfway through a body, the client's connection is cut, since its response has already started, and
the transaction is recorded as an error.

The cap applies to the body as the client receives it: a compressed upstream body is measured once decoded, for the
recording and for the cache alike.

Still buffered:

- Request bodies are read in full before anything is sent upstream, and held in memory
  (`#1130 <https://github.com/msqd/harp/issues/1130>`_).
- Responses that stay open, such as server-sent events and long-polling, are not supported yet: the transaction lasts as
  long as the response, and the http client's read timeout cuts a stream that stays silent for longer
  (`#1129 <https://github.com/msqd/harp/issues/1129>`_).

Remote urls carrying credentials
--------------------------------

An endpoint url may carry credentials (``https://user:password@api.example.com/``). They are sent
upstream as ``Authorization: Basic``, never in the ``Host`` header, and left out of recorded urls and
logs. An ``Authorization`` header already on the request, from the client or a rule, wins: the url
credentials only apply when there is none.

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

Shapes an upstream may reduce to a dot segment after its own normalisation are refused too, so none
of them relies on the upstream's behaviour:

- ``..;`` and ``.;`` segments (parameters dropped by Tomcat, Spring): ``/..;/..;/admin``,
  ``/%2e%2e;/admin``;
- double or deeper encoding: ``/%252e%252e/admin``;
- overlong UTF-8 dots: ``/%c0%ae%c0%ae/admin``;
- a dot segment followed by an encoded NUL: ``/%2e%2e%00/x``;
- Unicode look-alike dots (fullwidth ``．`` U+FF0E, sent as ``%EF%BC%8E``): ``/%EF%BC%8E%EF%BC%8E/x``.

Legitimate paths are forwarded unchanged: ``/a%2eb``, ``/%20``, ``/%C3%A9``, ``/page;jsessionid=abc``.

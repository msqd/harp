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
- names up to 64 characters (``max_name_length``), values up to 256 (``max_value_length``). Oversized tags are dropped
  first and do not count towards the 20.

Dropped tags are logged at debug level with the transaction id, never their value.

.. code-block:: yaml

    proxy:
      tags:
        max_count: 20
        max_name_length: 64
        max_value_length: 256

Tagging stays open: any name is accepted. If HARP is exposed to untrusted callers, strip ``x-harp-*`` headers from the
requests you do not trust (at your load balancer or gateway), or lower these bounds, since every kept tag is stored.

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

HARP credentials
----------------

A cookie is scoped to a host, not to a port: a browser signed in to the dashboard sends its session cookie to every proxy
port on the same host. HARP's own credentials never reach an origin, so the proxy removes them from the request before
forwarding it:

- the dashboard session cookie (``__Host-harp_session`` over HTTPS, ``harp_session`` over HTTP) is removed from
  ``Cookie``. The other cookies are kept, and the header is dropped when nothing is left;
- an ``Authorization: Bearer`` header whose value is a HARP token (``harp_`` prefix and valid checksum) is removed. Any
  other bearer is forwarded unchanged.

The removal happens before the request is recorded, so the stored transaction does not hold them either, whatever the
redaction settings say. When something was removed, the transaction carries the ``harp-credentials-stripped`` :doc:`marker </apps/storage/markers>`.
No setting turns this off, and no other header is touched.

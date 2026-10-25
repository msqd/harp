HTTP Cache
==========

.. tags:: applications

.. versionadded:: 0.10

The ``harp_apps.http_cache`` application provides RFC 9111-compliant HTTP caching for the HTTP client. It was
extracted from ``harp_apps.http_client`` as a separate application to enable better modularity and reuse.

The caching mechanism is implemented using `Hishel <https://hishel.com/>`_, a powerful HTTP caching library
that follows the HTTP caching standards defined in RFC 9111.

.. toctree::
    :hidden:
    :maxdepth: 1

    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.http_cache>


Overview
::::::::

The HTTP cache application provides efficient and standards-compliant HTTP response caching. It integrates
seamlessly with the ``http_client`` application to reduce redundant network calls by storing and reusing
responses according to RFC 9111 caching rules.

The cache automatically handles:

- **Freshness lifetime calculation** using max-age, s-maxage, and Expires headers
- **Cache revalidation** with ETags and Last-Modified headers
- **Vary matching**, so a stored response is never reused for a request whose selecting headers differ
- **Cache directives** including no-store, no-cache, private, public, and must-revalidate

Variants of a ``Vary`` resource
:::::::::::::::::::::::::::::::

A cache key holds up to **8 variants** of its resource, one per distinct value of the request headers the response
varies on, so a caller alternating between ``Accept: text/html`` and ``Accept: application/json`` is served from the
cache each time. The limit is ``harp_apps.http_cache.storages.MAX_VARIANTS_PER_KEY``. Storing a ninth variant evicts the
oldest stored one. Storing a variant again, with the same selecting headers, replaces it. Each variant expires on its
own, after the storage ``ttl``.

A cache entry is a ``cache/meta`` blob holding the list of its variants, oldest first. Entries written before this
version hold a single entry and are read as one variant. They are rewritten in the new format the next time their key is
written, which makes them unreadable by an earlier version.

.. versionchanged:: 0.13

    A cache key used to hold a single entry, so variants of a resource evicted each other.


Concurrent misses
:::::::::::::::::

When several requests for one variant of a resource miss together, one of them fetches from the origin and the others wait
for the stored entry, then are served from it. Requests for another variant, or for another endpoint, do not wait for it.
The coalescing is within one HARP process.

A request never fails because of it. It waits at most ``coalescing_timeout`` seconds (30 by default, a
``transport.arguments`` entry), and fetches on its own if the leading fetch fails, takes longer, or leaves nothing to
share: a response that cannot be stored, or one the cache does not retain.

On a cold key the ``Vary`` of the resource is not known until the first response arrives, so a request for another
variant waits for that response's headers, not for its body.

.. versionadded:: 0.13


Features
::::::::

- **RFC 9111 Compliance:** Implements HTTP caching standards for freshness, validation, and cache control
- **Shared Cache Mode:** Designed for shared cache scenarios (e.g., proxy caching for multiple clients)
- **Normalized Cache Keys:** Handles load-balanced backends by normalizing URLs for consistent cache keys
- **Flexible Storage:** Supports multiple storage backends via the storage application
- **Configurable Policy:** Customize caching behavior through policy configuration


.. note::

    Credentials are :doc:`redacted </apps/storage/redaction>` in what the cache stores. A response that varies on,
    carries (``Set-Cookie``) or was requested with a redacted value is not cached at all, unless you opt the name out of
    redaction.

.. _http-cache-shared:

.. warning::

    This is a **shared** cache: a stored response is served to any later caller whose request maps to the
    same key, and the key does not include who is asking. Before enabling it in front of an API that
    authenticates by cookie, ``Authorization`` or an API-key header, make sure the upstream marks per-caller
    responses with ``Cache-Control: private`` or with a ``Vary`` naming the header that identifies the caller.
    HARP honours both, and does not guess which of your headers carry an identity.

    - ``Cache-Control: private`` keeps a response out of the shared cache altogether::

        HTTP/1.1 200 OK
        Cache-Control: private, max-age=60

    - ``Vary: X-Api-Key`` makes a stored response reusable only for a request carrying the same
      ``X-Api-Key`` value::

        HTTP/1.1 200 OK
        Cache-Control: max-age=60
        Vary: X-Api-Key

    Without one of them, the first caller's response is served to the next one until it expires.


Loading
:::::::

The HTTP cache application is loaded automatically when present and not disabled. It depends on the
``http_client`` application, which is loaded with the default set.

To manually control loading, list the applications to load, dependencies included. The list replaces the default set
(``--applications`` replaces the file's list; ``--enable`` and ``--disable`` apply after either; with
several ``--file``, the last one that sets ``applications:`` wins). An unknown name fails at startup:

.. code-block:: yaml

    applications:
      - http_client  # Required by http_cache, not auto-loaded from a list
      - http_cache

    http_cache:
      enabled: true  # Set to false to disable


Configuration
:::::::::::::

Basic configuration
-------------------

Here's a basic cache configuration:

.. literalinclude:: ./examples/cache.yml
    :language: yaml

The cache uses sensible RFC 9111-compliant defaults. For detailed configuration options and
advanced customization, see :doc:`settings`.


How it works
::::::::::::

Request flow
------------

1. **Request arrives** at the HTTP client
2. **Cache lookup** checks if a fresh cached response exists
3. **Vary header matching** ensures the correct variant is selected
4. **Freshness check** determines if the cached response is still fresh
5. **Return cached response** if fresh, or forward to origin server if stale/missing
6. **Store response** from origin server for future requests, once its body has been passed on to the client

Response size
-------------

.. versionadded:: 0.12

The cache passes an origin's body on as it arrives and stores the response once the whole body has gone
through. A body larger, once decoded, than the proxy's recording cap (``proxy.max_recorded_body_size``, 1 MiB by default, see
:ref:`proxy-buffering-and-streaming`) is sent to the client whole and **not stored**: the next request for it goes
to the origin again. A response the client stopped reading before its end is not stored either.


Revalidation
------------

.. versionchanged:: 0.10

    Revalidation requests carry their validator again, and a ``304`` freshens the stored entry.

When a stored response goes stale, HARP does not simply fetch it again. If the origin provided a
validator, HARP asks whether anything changed and re-sends the body only if it did:

- an ``ETag`` is sent back as ``If-None-Match``, a ``Last-Modified`` as ``If-Modified-Since``
- a ``304 Not Modified`` costs no body transfer. HARP updates the stored entry's headers from the
  ``304``, which restarts its freshness lifetime, and serves the client from the stored body
- a ``200`` replaces the stored entry with the new representation

So a resource that changes rarely is fetched in full once and then confirmed with small
round trips, rather than being downloaded again at every freshness boundary. A resource the origin
offers no validator for is simply fetched again, since there is nothing to revalidate with.

.. note::

    HARP computes a stored response's age from its ``Date`` header (RFC 9111 §4.2.3). When an
    origin sends no ``Date``, HARP adds one set to the time it received the response before
    storing it (RFC 9110 §6.6.1), so the response still ages. A ``Date`` sent by the origin is kept
    as is. Responses that are forwarded but not stored are not modified.


Invalidation by unsafe requests
:::::::::::::::::::::::::::::::

.. versionadded:: 0.12

A successful write through the proxy drops the stored responses it made out of date (RFC 9111 §4.4), so a
client reading its own write gets the new body rather than the cached one. When the origin answers a
``PUT``, ``POST``, ``PATCH``, ``DELETE`` (any method other than ``GET``, ``HEAD``, ``OPTIONS`` and ``TRACE``)
with a ``2xx`` or ``3xx`` status, HARP invalidates:

- the target URI of the request;
- the URIs named by the response's ``Location`` and ``Content-Location`` headers, when they are on the same
  host as the target. A header pointing at another host is ignored.

An error response (``4xx``, ``5xx``) invalidates nothing. Invalidation applies within the endpoint that
handled the request, like the cache itself, and also when the request carries ``Cache-Control: no-store``.


.. _http-cache-purge:

Purging one entry
:::::::::::::::::

.. versionadded:: 0.13

An operator can remove a cached response before its ``ttl`` with a ``PURGE`` request to the proxy, on the port of the
endpoint that cached it::

    curl -X PURGE 'http://localhost:8080/path?query=1'

It is **off by default**. Turn it on, and say who may use it:

.. code-block:: yaml

    http_cache:
      purge:
        enabled: true
        allow: ["127.0.0.1", "10.0.0.0/8"]  # addresses or CIDR ranges

With purge enabled, the request is answered by HARP and **never sent upstream**:

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - Status
      - When
    * - ``200``
      - The target was cached: every stored variant of that URL (path and query string) is removed, within the endpoint
        that received the request.
    * - ``404``
      - Nothing is cached for that URL on that endpoint.
    * - ``403``
      - The peer is not in ``allow``. Nothing is removed.

The same path on another endpoint is not touched. There is no wildcard or prefix purge, and no purge across HARP
instances. With purge disabled (the default), a ``PURGE`` request is proxied like any other request.

.. warning::

    **Security default.** ``allow`` is empty by default, so nobody may purge, even with ``enabled: true``. The
    allow-list is the only protection: there is no authentication. Keep it narrow.

**Which address is checked.** The allow-list is matched against the address of the peer HARP is connected to, the same
address the proxy appends to ``X-Forwarded-For``. It never reads ``X-Forwarded-For``, ``Forwarded`` or any other header,
including those from a peer listed in :ref:`proxy.trusted_proxies <proxy-forwarding-headers>`: trusting a proxy tells HARP
which forwarded values to keep for the upstream, it does not change who is connected. A peer whose address is unknown is
refused.

This matters behind a reverse proxy or load balancer, where the peer is that proxy for every client. Listing the
proxy in ``allow`` then lets everyone behind it purge, so either filter ``PURGE`` at the proxy, or reach HARP directly
for purges (from the host, or through a private port) and list only those addresses. IPv4-mapped IPv6 addresses
(``::ffff:127.0.0.1``) are matched as their IPv4 address.


Cache key normalization
-----------------------

The cache includes special handling for load-balanced backends. When the proxy forwards requests to
different backend instances of the same logical endpoint, the cache normalizes URLs by using the
endpoint name instead of the actual backend host.

This ensures that requests to different backend instances (e.g., ``backend-1``, ``backend-2``) that
represent the same logical endpoint share the same cache key. The endpoint name is extracted from the
request extensions set by the proxy application.


Cache debugging headers
-----------------------

When the cache application is loaded, the proxy annotates every response it forwards:

- ``X-Cache: HIT`` when the response was served from HARP's cache, ``X-Cache: MISS`` otherwise.
- ``Age``, the number of seconds since HARP stored the response, on cache hits.

These headers are written for the benefit of whoever is looking at the response. They are not how
HARP knows a response came from its own cache: that comes from the cache itself, so an upstream
cannot influence what the dashboard reports.

.. note::

    If the upstream sets its own ``X-Cache`` or ``Age`` header, which is common when the origin sits
    behind a CDN, HARP replaces it with its own value. The header then describes HARP's cache, not
    the upstream's, and the upstream's own value does not reach the client. With the cache
    application disabled, HARP writes neither header and the upstream's values pass through
    untouched.


Cache-Control directives a client can send
------------------------------------------

.. versionchanged:: 0.10

    Request ``no-store`` is honoured again. It was honoured up to 0.9.1, and stopped being honoured
    when the cache migrated to hishel 1.x.

A caller can influence HARP's cache with the request directives of RFC 9111 §5.2.1:

.. list-table::
    :header-rows: 1
    :widths: 20 20 60

    * - Directive
      - Honoured
      - What HARP does
    * - ``no-store`` (§5.2.1.5)
      - yes
      - The request bypasses the cache entirely. Nothing about the exchange is stored, and an
        entry that already exists for that resource is not used to answer it. The request is
        proxied normally otherwise, and reported as ``X-Cache: MISS``.
    * - ``no-cache`` (§5.2.1.4)
      - yes
      - A stored response is revalidated against the origin before being reused.
    * - ``max-age``, ``max-stale``, ``min-fresh``, ``only-if-cached`` (§5.2.1.1–3, §5.2.1.7)
      - yes
      - Handled by hishel's RFC 9111 implementation.

The response directives of §5.2.2 (``no-store``, ``no-cache``, ``private``, ``public``,
``must-revalidate``, ``max-age``, ``s-maxage``) are honoured as the specification defines them.

.. warning::

    These directives bind HARP's **cache**. They do not bind HARP's **transaction record**, which is
    a separate store with a separate purpose. See :ref:`what-harp-retains` below before treating
    ``no-store`` as a retention control.


.. _what-harp-retains:

What HARP retains, and what a caller can do about it
::::::::::::::::::::::::::::::::::::::::::::::::::::

**Recording is best-effort.** HARP records the transactions passing through it, including requests
carrying ``Cache-Control: no-store``, and a recorded transaction holds the request headers, the
response headers and both bodies, persisted to the storage application and shown in the dashboard.
Under load it holds less than that: as the storage worker falls behind it drops message detail
first, and whole transactions once it falls further behind, rather than slowing traffic down to
finish writing. An empty payload panel in the dashboard can therefore mean the payload was shed,
not that nothing was sent, and a transaction can be missing altogether. See
`#945 <https://github.com/msqd/harp/issues/945>`_ for what was measured and how far it goes.

Treat the transaction record as an operational view of your traffic rather than a complete one.

The cache and the transaction record retain for different reasons. A cache retains in order to
answer the *next* caller, which is why ``no-store`` binds it: the directive is about reuse. The
transaction record retains in order to show operators what passed through their own proxy, and
nothing in it is ever read back into a response.

**A caller's** ``no-store`` **binds the cache and suppresses the payload of the transaction record.**
Such a request is not served from a stored entry and nothing about it is cached. It is still
recorded, with its summary (method, path and query string) and its timing, but neither its headers
nor its body are stored, and neither are those of the response. The transaction carries the markers
``no-store-request`` and ``no-store-response``, and the dashboard says the payload was not recorded
and why, which tells it apart from a payload shed under load.

**An origin's** ``no-store`` **suppresses its own response payload only.** The response headers and
body are not stored and the transaction carries ``no-store-response``; the request is recorded
normally, since it is evidence of what was asked of a third party.

.. versionchanged:: 0.13
   Up to 0.12, a ``no-store`` of either side was recorded like any other message.

.. warning::

    HARP does not currently provide a way to override this. An override is owed, and the intended
    mechanism is the transaction markers. The decision is recorded in
    `ADR-0002 <https://github.com/msqd/harp/blob/main/docs/adr/0002-caller-no-store-suppresses-payload-recording.md>`_.
    The query string and path of the request summary are still stored: see :doc:`/apps/storage/redaction`.

Note also what RFC 9111 §5.2.1.5 says of the directive: it "is not a reliable or sufficient
mechanism for ensuring privacy. In particular, malicious or compromised caches might not recognize
or obey this directive." Whatever an intermediary does with it, a caller can infer nothing about
retention from having sent it.

**Suppressing what gets recorded is currently the operator's decision.** It is made with the
:doc:`rules application </apps/rules/index>`, which can set the transaction markers documented in
:doc:`/apps/storage/markers` to skip storing request or response headers and bodies for the traffic
you choose.


RFC 9111 test coverage
::::::::::::::::::::::

The cache is tested against RFC 9111 requirements at the **policy** level, meaning what the cache
decides to store, reuse or revalidate. The suite covers:

- **Freshness lifetime** (§4.2): max-age, s-maxage, Expires headers
- **Validation** (§4.3): ETag, Last-Modified, conditional requests
- **Cache-Control request directives** (§5.2.1): no-store, no-cache
- **Cache-Control response directives** (§5.2.2): no-store, no-cache, private, public
- **HTTP methods** (§3): GET, HEAD, POST, PUT, DELETE, PATCH cacheability
- **Status codes** (§3): cacheable responses (200, 301, 404, etc.)

The suite lives in ``harp_apps/http_cache/tests/rfc9111/``.

.. warning::

    **Read this before citing the suite as evidence of compliance.** Most of it runs against a storage double,
    which holds several entries per cache key and applies no ``ttl``. It is evidence about what the policy
    *decides to store*; what the storage *retains* is covered by the tests that run against ``AsyncStorage``
    itself.


Configuration reference
:::::::::::::::::::::::

For complete configuration options and examples, see :doc:`settings`.


Internal implementation
:::::::::::::::::::::::

The internal implementation leverages the following classes:

- :class:`HttpCacheSettings <harp_apps.http_cache.settings.HttpCacheSettings>` - Cache configuration
- :class:`AsyncCacheTransport <harp_apps.http_cache.transports.AsyncCacheTransport>` - Transport wrapper
- :class:`AsyncStorage <harp_apps.http_cache.storages.AsyncStorage>` - Storage adapter
- :class:`WrappedRequest <harp_apps.http_cache.models.WrappedRequest>` - Request normalization


Further reading
:::::::::::::::

- `RFC 9111: HTTP Caching <https://www.rfc-editor.org/rfc/rfc9111.html>`_
- `Hishel Documentation <https://hishel.com/>`_
- `HTTP Caching Best Practices <https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching>`_

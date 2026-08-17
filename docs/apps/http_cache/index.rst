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

.. note::

    ``Vary`` is matched correctly but currently buys you no reuse. The storage holds one entry per
    cache key, so two variants of the same resource overwrite each other, and a caller alternating
    between them gets no cache hits at all. Nobody is served the wrong variant; they are served no
    cache. This is not new in 0.10, the behaviour is the same on 0.9.1, and it is tracked in
    `#910 <https://github.com/msqd/harp/issues/910>`_.


Features
::::::::

- **RFC 9111 Compliance:** Implements HTTP caching standards for freshness, validation, and cache control
- **Shared Cache Mode:** Designed for shared cache scenarios (e.g., proxy caching for multiple clients)
- **Normalized Cache Keys:** Handles load-balanced backends by normalizing URLs for consistent cache keys
- **Flexible Storage:** Supports multiple storage backends via the storage application
- **Configurable Policy:** Customize caching behavior through policy configuration


Loading
:::::::

The HTTP cache application is loaded automatically when present and not disabled. It depends on the
``http_client`` application, which will be loaded automatically if not already present.

To manually control loading:

.. code-block:: yaml

    applications:
      - http_cache  # Will auto-load http_client as dependency

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
6. **Store response** from origin server for future requests


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

    HARP computes a stored response's age from its ``Date`` header (RFC 9111 §4.2.3). An origin
    that sends no ``Date`` gives the cache nothing to age its response against.


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
Under load it holds less than that: storage sheds whole transactions, and then message detail within
the transactions it does keep, rather than slowing traffic down to finish writing. An empty payload
panel in the dashboard can therefore mean the payload was shed, not that nothing was sent. See
`#945 <https://github.com/msqd/harp/issues/945>`_ for what was measured and how far it goes.

Treat the transaction record as an operational view of your traffic rather than a complete one.

The cache and the transaction record retain for different reasons. A cache retains in order to
answer the *next* caller, which is why ``no-store`` binds it: the directive is about reuse. The
transaction record retains in order to show operators what passed through their own proxy, and
nothing in it is ever read back into a response.

**In 0.10, a caller's** ``no-store`` **binds the cache and does not affect the transaction record.**
Such a request is not served from a stored entry and nothing about it is cached, and it is recorded
like any other request. Whether a caller may suppress payload recording is decided in
`#927 <https://github.com/msqd/harp/issues/927>`_ and lands in 0.11, so do not build on the current
behaviour in either direction.

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

    **Read this before citing the suite as evidence of compliance.** It runs against a storage
    double, not against the storage that ships. The double holds several entries per cache key;
    ``AsyncStorage`` holds one, as its own docstring says. So the suite is evidence about what the
    policy *decides to store*, and no evidence at all about what the storage *retains*.

    ``Vary`` (§4.1) is where that difference bites, and it is why ``Vary`` is not in the list above.
    The double can hold two variants side by side and the shipped storage cannot, so those tests
    pass on a behaviour that does not work in production. See
    `#910 <https://github.com/msqd/harp/issues/910>`_ for the behaviour and
    `#965 <https://github.com/msqd/harp/issues/965>`_ for why the tests do not catch it.


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

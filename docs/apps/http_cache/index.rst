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
- **Content negotiation** via Vary header support
- **Cache directives** including no-store, no-cache, private, public, and must-revalidate


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

**HARP records every transaction passing through it, including requests carrying**
``Cache-Control: no-store``. The request headers, the response headers and both bodies are
persisted to the storage application and shown in the dashboard. This is deliberate and it is not
affected by the cache honouring the directive.

The cache and the transaction record retain for different reasons. A cache retains in order to
answer the *next* caller, which is why ``no-store`` binds it: the directive is about reuse. The
transaction record retains in order to show operators what passed through their own proxy, and
nothing in it is ever read back into a response.

Two reasons this is the deliberate answer rather than an omission:

- **A client must not be able to switch off an operator's audit trail by setting a request header.**
  If ``no-store`` suppressed recording, any caller, including one behaving badly, could remove its
  own traffic from the record of the proxy it is passing through. That inverts who the record is
  for.
- RFC 9111 §5.2.1.5 states outright that the directive "is not a reliable or sufficient mechanism
  for ensuring privacy. In particular, malicious or compromised caches might not recognize or obey
  this directive." A caller can therefore infer nothing about retention from it, and an operator can
  promise nothing by honouring it.

**Suppressing what gets recorded is the operator's decision, not the caller's.** It is made with the
:doc:`rules application </apps/rules/index>`, which can set the transaction markers documented in
:doc:`/apps/storage/markers` to skip storing request or response headers and bodies for the traffic
you choose.


RFC 9111 Compliance
:::::::::::::::::::

The cache implementation is tested against RFC 9111 requirements. The test suite includes:

- **Freshness lifetime** (§4.2): max-age, s-maxage, Expires headers
- **Validation** (§4.3): ETag, Last-Modified, conditional requests
- **Cache-Control request directives** (§5.2.1): no-store, no-cache
- **Cache-Control response directives** (§5.2.2): no-store, no-cache, private, public
- **Vary header** (§4.1): content negotiation and cache key selection
- **HTTP methods** (§3): GET, HEAD, POST, PUT, DELETE, PATCH cacheability
- **Status codes** (§3): cacheable responses (200, 301, 404, etc.)

See the test suite in ``harp_apps/http_cache/tests/rfc9111/`` for detailed compliance verification.


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

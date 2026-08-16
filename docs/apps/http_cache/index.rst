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


RFC 9111 Compliance
:::::::::::::::::::

The cache implementation is tested against RFC 9111 requirements. The test suite includes:

- **Freshness lifetime** (§4.2): max-age, s-maxage, Expires headers
- **Validation** (§4.3): ETag, Last-Modified, conditional requests
- **Cache-Control directives** (§5.2.2): no-store, no-cache, private, public
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

HTTP Cache Settings
===================

.. tags:: settings

The ``http_cache`` application provides configuration options for controlling HTTP caching behavior according
to RFC 9111 standards.

Examples
::::::::

Here is an example containing all default values for the ``http_cache`` application settings:

.. literalinclude:: ./examples/reference.yml
    :language: yaml


Reference
:::::::::

Implementation (python): :class:`HttpCacheSettings <harp_apps.http_cache.settings.HttpCacheSettings>`

.. jsonschema:: ./schema.json
   :pointer: /$defs/HttpCacheSettings


Configuration options
:::::::::::::::::::::

enabled
-------

**Type:** ``bool``

**Default:** ``true``

Global cache flag. Set to ``false`` to completely disable caching.

.. code-block:: yaml

    http_cache:
      enabled: false


transport
---------

**Type:** :class:`Service <harp.config.Service>`

**Default:** ``harp_apps.http_cache.transports.AsyncCacheTransport``

The cache transport wraps the HTTP client transport to intercept requests and responses for caching.
This is typically a ``hishel._async_httpx.AsyncCacheTransport`` instance or subclass.

The default implementation (``AsyncCacheTransport``) extends Hishel's transport with:

- Normalized cache keys for load-balanced backends
- Integration with HARP's storage system

.. code-block:: yaml

    http_cache:
      transport:
        type: harp_apps.http_cache.transports.AsyncCacheTransport
        arguments:
          # Custom transport arguments (optional)


policy
------

**Type:** :class:`Service <harp.config.Service>`

**Default:** ``hishel.SpecificationPolicy`` with RFC 9111-compliant options

The cache policy determines what responses are cacheable and how to handle cache revalidation.

Hishel uses ``SpecificationPolicy`` with ``CacheOptions`` to configure caching behavior:

- **shared:** Whether this is a shared cache (default: ``true``)
- **supported_methods:** HTTP methods to cache (default: ``["GET", "HEAD"]``)
- **allow_stale:** Whether to serve stale responses (default: ``false``)

.. code-block:: yaml

    http_cache:
      policy:
        type: hishel.SpecificationPolicy
        arguments:
          cache_options:
            shared: true
            supported_methods: [GET, HEAD]
            allow_stale: false


storage
-------

**Type:** :class:`Service <harp.config.Service>`

**Default:** ``harp_apps.http_cache.storages.AsyncStorage``

The storage backend for cached responses. By default, it uses the storage application's blob storage
(``storage.blobs``), with an in-memory fallback if no blob storage is configured.

The default storage includes:

- **ttl:** Time-to-live for cache entries (default: ``None`` - no TTL)
- **check_ttl_every:** How often to check for expired entries in seconds (default: ``60.0``)
- **allow_heuristics:** Whether to retain responses with no explicit expiry (default: ``false``)

.. code-block:: yaml

    http_cache:
      storage:
        type: harp_apps.http_cache.storages.AsyncStorage
        arguments:
          ttl: 3600  # Expire all cache entries after 1 hour
          check_ttl_every: 120  # Check every 2 minutes


.. _http-cache-allow-heuristics:

allow_heuristics
----------------

**Type:** ``bool``

**Default:** ``false``

RFC 9111 section 4.2.2 lets a cache invent a freshness lifetime for a response the origin never
declared cacheable, deriving it from the ``Last-Modified`` date. HARP does not do this by default.

The reason is a trust boundary rather than compliance. HARP's cache key is derived from the request
URL alone, so no request header takes part in it. RFC 9111 makes a shared cache refuse to reuse a
response to a request carrying ``Authorization``, but it says nothing about the many other ways an
API authenticates its callers: a session cookie, ``X-Api-Key``, a bearer token in a vendor header.
An upstream that answers with a ``Last-Modified`` and no ``Cache-Control`` at all, which is common,
would then have one caller's response handed to the next one.

A response is therefore only retained when the origin stated how long it stays fresh, through
``Cache-Control: s-maxage``, ``Cache-Control: max-age`` or ``Expires``.

Turn it on if you know your upstreams do not serve per-caller responses, or mark them correctly with
``Cache-Control: private`` and ``Vary``:

.. code-block:: yaml

    http_cache:
      storage:
        arguments:
          allow_heuristics: true

.. note::

    Whether heuristics are on or off, this is a **shared** cache. An upstream serving responses that
    differ per caller must say so, with ``Cache-Control: private`` or with a ``Vary`` naming the
    header that distinguishes them. HARP honours both, and will not guess which of your headers
    carries an identity.


Custom implementations
::::::::::::::::::::::

You can provide custom implementations for any of the service components:

Custom policy example
---------------------

.. code-block:: yaml

    http_cache:
      policy:
        type: my_app.custom_cache.StrictPolicy
        arguments:
          max_age_override: 300  # Force 5-minute max-age


Custom storage example
----------------------

.. code-block:: yaml

    http_cache:
      storage:
        type: my_app.custom_cache.RedisStorage
        arguments:
          url: redis://localhost:6379/1
          prefix: "harp:cache:"


Best practices
::::::::::::::

Production configuration
------------------------

For production deployments:

1. **Use Redis or database blob storage** instead of in-memory fallback
2. **Set appropriate TTL** to prevent unbounded cache growth
3. **Configure shared cache mode** (``shared: true``) for proxy scenarios

.. code-block:: yaml

    storage:
      blobs:
        type: harp_apps.storage.services.blob_storages.redis.RedisBlobStorage
        arguments:
          url: redis://cache-server:6379/0

    http_cache:
      enabled: true
      policy:
        type: hishel.SpecificationPolicy
        arguments:
          cache_options:
            shared: true
            supported_methods: [GET, HEAD]
            allow_stale: false


Development configuration
--------------------------

For development and testing:

1. **Use in-memory storage** for faster iteration
2. **Disable caching** when debugging specific issues

.. code-block:: yaml

    http_cache:
      enabled: true
      storage:
        type: harp_apps.http_cache.storages.AsyncStorage
        # Uses in-memory fallback by default

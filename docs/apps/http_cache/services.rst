HTTP Cache Services
===================

.. tags:: services

The services defined by the ``http_cache`` application provide the caching infrastructure for the HTTP client.
Services are conditionally registered based on whether caching is enabled.


When cache is enabled
:::::::::::::::::::::

When the cache is enabled (default), the following services are available:

.. autoservices:: harp_apps.http_cache
   :file: ../../../harp_apps/http_cache/services.yml
   :namespace: http_cache
   :settings: {"enabled": true}


Service descriptions
::::::::::::::::::::

http_cache.transport
--------------------

**Type:** ``harp_apps.http_cache.transports.AsyncCacheTransport``

The caching transport wraps the HTTP client's proxy transport to intercept requests and responses.
It extends Hishel's ``AsyncCacheTransport`` with:

- **Cache key normalization:** Ensures consistent cache keys for load-balanced backends
- **Debug headers:** Adds ``X-Cache`` (HIT/MISS) and ``Age`` headers to responses
- **Storage integration:** Uses HARP's blob storage system

This service overrides the ``http_client`` transport to enable caching.

Dependencies:

- ``http_client.proxy_transport`` - The underlying HTTP transport
- ``http_cache.storage`` - Cache storage backend
- ``http_cache.policy`` - Cache policy for determining cacheability


http_cache.policy
-----------------

**Type:** ``hishel.SpecificationPolicy``

The cache policy implements RFC 9111 caching rules to determine:

- Which responses are cacheable
- How long responses remain fresh
- When revalidation is required
- Which cache directives to respect

Uses ``http_cache.policy.options`` for configuration.

Dependencies:

- ``http_cache.policy.options`` - Cache options configuration


http_cache.policy.options
--------------------------

**Type:** ``hishel.CacheOptions``

Cache options that control policy behavior:

- **shared:** ``true`` - Operate as a shared cache (not private browser cache)
- **supported_methods:** ``["GET", "HEAD"]`` - Cacheable HTTP methods
- **allow_stale:** ``false`` - Don't serve stale responses without revalidation
- **allow_heuristics:** ``false`` - Don't use heuristic freshness calculation

These options follow RFC 9111 best practices for HTTP proxy caching.


http_cache.storage
------------------

**Type:** ``harp_apps.http_cache.storages.AsyncStorage``

The storage backend for cached HTTP responses. Adapts Hishel's storage interface to HARP's blob
storage system.

Features:

- **TTL support:** Automatic expiration of old cache entries
- **Periodic cleanup:** Background cleanup of expired entries
- **Blob storage integration:** Uses ``storage.blobs`` service when available
- **Fallback storage:** Uses in-memory storage if no blob storage is configured

Dependencies:

- ``storage.blobs`` (optional) - Blob storage from storage application
- ``http_cache.fallback_blob_storage`` - Fallback if no blob storage available


http_cache.fallback_blob_storage
---------------------------------

**Type:** ``harp_apps.storage.services.blob_storages.memory.MemoryBlobStorage``

In-memory blob storage used as a fallback when the storage application doesn't provide blob storage.

.. warning::
   This fallback storage is not suitable for production use. Configure proper blob storage
   (Redis, PostgreSQL, etc.) via the storage application for production deployments.


Integration with http_client
:::::::::::::::::::::::::::::

The ``http_cache`` application integrates with ``http_client`` by overriding its transport service.
This happens during the application binding phase:

1. **http_client** registers its transport (``http_client.transport``)
2. **http_cache** wraps it with caching transport (``http_cache.transport``)
3. **http_client.transport** is overridden to use the caching transport

This ensures that all HTTP requests made through the client are cached according to the configured
policy.


Customizing services
::::::::::::::::::::

You can customize any of these services by overriding their configuration:

Custom policy
-------------

.. code-block:: yaml

    http_cache:
      policy:
        type: my_app.CustomCachePolicy
        arguments:
          custom_option: value


Custom storage
--------------

.. code-block:: yaml

    http_cache:
      storage:
        type: my_app.CustomCacheStorage
        arguments:
          storage_url: redis://localhost:6379/1

See :doc:`settings` for all configuration options including how to disable caching.

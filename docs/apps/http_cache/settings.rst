HTTP Cache Settings
===================

.. tags:: settings

The ``http_cache`` application provides configuration options for controlling HTTP caching behavior according
to RFC 9111 standards.

.. note::

    Nothing here changes what a **caller** can ask for. For the ``Cache-Control`` request directives
    HARP honours, and for what HARP retains regardless of them, see :ref:`what-harp-retains`.

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

Hishel's ``SpecificationPolicy`` is configured with ``CacheOptions``, which you set through
``policy.options``. Unknown keys are rejected at load.

.. code-block:: yaml

    http_cache:
      policy:
        options:
          shared: true
          supported_methods: [GET, HEAD]
          allow_stale: false

policy.options.shared
~~~~~~~~~~~~~~~~~~~~~

**Type:** ``bool``, **Default:** ``true``

Behave as a shared cache (RFC 9111). See the :ref:`shared cache warning <http-cache-shared>` before changing it.

policy.options.supported_methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Type:** ``list[str]``, **Default:** ``[GET, HEAD]``

HTTP methods whose responses can be cached.

policy.options.allow_stale
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Type:** ``bool``, **Default:** ``false``

Serve a stale entry from the cache instead of refetching it from the origin.


purge
-----

.. versionadded:: 0.13

**Default:** ``enabled: false``, ``allow: ["127.0.0.1"]``

Removal of one cache entry with a ``PURGE`` request, see :ref:`http-cache-purge`.

purge.enabled
~~~~~~~~~~~~~

**Type:** ``bool``, **Default:** ``false``

Answer ``PURGE`` requests (``200``, ``404`` or ``403``) instead of proxying them.

purge.allow
~~~~~~~~~~~

**Type:** ``list`` of IP addresses or CIDR ranges, **Default:** ``["127.0.0.1"]``

The peer addresses HARP is connected to that may purge, whatever forwarding headers say. A peer outside the list gets
``403``, and an empty list refuses everyone. The default allows IPv4 loopback only, not ``::1``.

.. code-block:: yaml

    http_cache:
      purge:
        enabled: true
        allow: ["127.0.0.1", "10.0.0.0/8"]


storage
-------

**Type:** :class:`Service <harp.config.Service>`

**Default:** ``harp_apps.http_cache.storages.AsyncStorage``

The storage backend for cached responses. By default, it uses the storage application's blob storage
(``storage.blobs``), with an in-memory fallback if no blob storage is configured.

The default storage includes:

- **ttl:** Seconds after which an entry is expired, counted from when it was stored or last freshened by a ``304``
  (default: ``86400``, 24 hours). An entry with a longer ``max-age`` is still expired after ``ttl``. ``null`` disables
  expiry by age. Each variant of a ``Vary`` resource expires on its own. An expired entry is not served and, once none of its key's variants is left, its ``cache/meta`` blob is deleted. The header and body blobs it
  pointed at are then removed by the :doc:`janitor </apps/janitor/index>`.
- **check_ttl_every:** Minimum seconds between two sweeps deleting expired entries, per process (default: ``60.0``).
  A sweep runs in the background, never inside a proxied request.
  Needs a blob storage that can list its entries (SQL); with Redis, a warning is logged at startup and only entries
  that are read again expire.
- **allow_heuristics:** Whether to serve responses with no explicit expiry without asking the origin (default: ``false``)

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

A response is therefore only served from the cache without asking the origin when the origin stated
how long it stays fresh, through ``Cache-Control: s-maxage``, ``Cache-Control: max-age`` or ``Expires``.

A response with no such expiry but an ``ETag`` or a ``Last-Modified`` is still retained (see the credential rule below), and never
served without the origin confirming it: each use sends a conditional request (``If-None-Match``,
``If-Modified-Since``), a ``304 Not Modified`` serves the stored body and a ``200`` serves, and
replaces it, with the new one. Only the body transfer is saved. With the origin unreachable the request
fails, the stored response is not served. A response with neither an expiry nor a validator, or with
``Cache-Control: no-cache``, is not retained.

A conditional request proves that the validator still matches, not that the stored body belongs to the caller:
an origin comparing only validators would answer ``304`` to another caller, who would get the first one's body.
So such a response is retained only when its request carried none of the transaction's credential headers
(``Authorization``, ``Proxy-Authorization``, ``Cookie`` and any name a rule adds to ``transaction.redaction.headers``)
and the response carries no ``Set-Cookie``. Otherwise it is not retained. A credential sent under a header no rule
declares is invisible to the cache: if your upstream authenticates callers with one (``X-Api-Key``, say),
declare it as a credential.

Known limits: entries stored while ``allow_heuristics`` was ``true`` and read after turning it off are revalidated
too, like any entry without an expiry. With ``allow_stale`` turned on in the policy options, such a response is served stale like any
other, without asking the origin. While several ``Vary`` variants of one resource are retained this way, which
one a request revalidates is hishel's choice, not the most recently stored.

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
    carries an identity. See the :ref:`shared cache warning <http-cache-shared>`.


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
        options:
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

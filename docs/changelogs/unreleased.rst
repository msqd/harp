Unreleased
==========

Added
-----

- Added cache debugging headers to HTTP responses:

  - ``X-Cache: MISS`` header on non-cached responses
  - ``X-Cache: HIT`` header on cached responses
  - ``Age`` header showing cache age in seconds for cached responses
- Application dependency resolution with topological sorting to ensure correct initialization order
- ApplicationSettingsMixin for standardized enable/disable functionality in application settings
- ``autoload_dependencies`` parameter for ``ApplicationsRegistry.add()`` to automatically load declared dependencies
- ``--strict`` CLI flag for enforcing strict configuration validation
- Warning system for misconfigured applications (config exists for unloaded apps)
- Two-pass configuration parsing to filter applications with ``enabled: false``

- Added normalized cache key generation for load balancing support:

  - Cache keys now exclude protocol, hostname, and port from URLs
  - Resources accessed via different backend servers share cache entries
  - Implemented via custom ``AsyncCacheTransport`` that normalizes URLs
  - Maintains full HTTP RFC compliance including Vary header support

Changed
-------

**BREAKING CHANGE**: Migrated HTTP client caching from hishel 0.1.x to hishel 1.0.x with new architecture.

- **New ``http_cache`` application**: Cache functionality has been moved to a dedicated ``http_cache`` application that depends on ``http_client``. This provides better separation of concerns.
- **Package restructuring**: All cache-related code moved from ``harp_apps.http_client.contrib.hishel.*`` to ``harp_apps.http_cache.*`` (flattened structure)
- **Configuration changes**: Cache configuration moved from ``http_client.cache.*`` to ``http_cache.*``
- Updated documentation examples to use new hishel 1.0 configuration (``policy`` instead of ``controller``)

- Cache policy now uses ``hishel.SpecificationPolicy`` with ``CacheOptions`` instead of ``hishel.Controller``
- The following cache configuration parameters are no longer available:

  - ``allow_heuristics`` - Hishel 1.0 strictly follows RFC 9111
  - ``cacheable_status_codes`` - Determined by RFC 9111 compliance
  - ``cacheable_methods`` → Use ``http_cache.policy`` service override with custom ``CacheOptions.supported_methods``
  - ``allow_stale`` → Use ``http_cache.policy`` service override with custom ``CacheOptions.allow_stale``

- Cached data from hishel 0.1.x remains fully compatible and readable
- **Note**: http_cache uses a temporary workaround in its ``on_bind`` event to configure http_client's transport. This will be replaced with proper cross-app service overrides once issue #806 is implemented
- If you're using custom cache configuration, update your config:

  **Old (hishel 0.1.x with http_client.cache)**::

    http_client:
      cache:
        enabled: true
        controller:
          type: hishel.Controller
          arguments:
            allow_stale: false
            cacheable_methods: [GET, HEAD]

  **New (hishel 1.0 with http_cache app)**::

    http_cache:
      enabled: true
      policy:
        type: hishel.SpecificationPolicy
        # Default CacheOptions are provided by services.yml
        # To customize, override the entire policy service
- Cookiecutter template migrated from Poetry to UV (PEP 621, Python 3.13, hatchling), with enhanced Makefile, improved prompts, and automatic git initialization.

Fixed
-----

- Fixed test discovery incorrectly including ``misc/`` directory worktree applications in ``test_all_applications_settings.py``
- Generated projects now properly isolate pytest tests and include correct startup instructions.

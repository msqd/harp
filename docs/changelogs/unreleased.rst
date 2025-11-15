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
- ``--strict`` CLI flag for enforcing strict configuration validation
- Warning system for misconfigured applications (config exists for unloaded apps)
- Two-pass configuration parsing to filter applications with ``enabled: false``

Changed
-------

**BREAKING CHANGE**: Migrated HTTP client caching from hishel 0.1.x to hishel 1.0.x.

- Updated documentation examples to use new hishel 1.0 configuration (``policy`` instead of ``controller``)

- The ``http_client.cache.controller`` configuration key has been renamed to ``http_client.cache.policy``
- Cache policy now uses ``hishel.SpecificationPolicy`` with ``CacheOptions`` instead of ``hishel.Controller``
- The following cache configuration parameters are no longer available:

  - ``allow_heuristics`` - Hishel 1.0 strictly follows RFC 9111
  - ``cacheable_status_codes`` - Determined by RFC 9111 compliance
  - ``cacheable_methods`` → Use ``cache.policy`` service override with custom ``CacheOptions.supported_methods``
  - ``allow_stale`` → Use ``cache.policy`` service override with custom ``CacheOptions.allow_stale``

- Cached data from hishel 0.1.x remains fully compatible and readable
- If you're using custom cache configuration, update your config:

  **Old (hishel 0.1.x)**::

    http_client:
      cache:
        controller:
          type: hishel.Controller
          arguments:
            allow_stale: false
            cacheable_methods: [GET, HEAD]

  **New (hishel 1.0)**::

    http_client:
      cache:
        policy:
          type: hishel.SpecificationPolicy
          # Default CacheOptions are provided by services.yml
          # To customize, override the entire policy service
- Cookiecutter template migrated from Poetry to UV (PEP 621, Python 3.13, hatchling), with enhanced Makefile, improved prompts, and automatic git initialization.

Fixed
-----

- Fixed test discovery incorrectly including ``misc/`` directory worktree applications in ``test_all_applications_settings.py``
- Generated projects now properly isolate pytest tests and include correct startup instructions.

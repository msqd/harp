from harp.config import Configurable, Service

# HTTP status codes that are heuristically cacheable according to RFC 9111
# Migrated from hishel 0.1.x to avoid dependency on internal APIs
HEURISTICALLY_CACHEABLE_STATUS_CODES = (200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501)


class CacheSettings(Configurable):
    #: Global cache flag, set to false to disable caching.
    enabled: bool = True

    #: Cache transport to use for the client. This is usually a hishel._async_httpx.AsyncCacheTransport (or subclass) instance.
    transport: Service = Service(type="hishel._async_httpx.AsyncCacheTransport")

    # Note: hishel 1.0 uses SpecificationPolicy with CacheOptions instead of Controller
    # The policy system is more flexible but has a different API
    # For now, we'll use the default SpecificationPolicy until we implement CacheOptions wrapper
    controller: Service = Service(
        type="hishel.SpecificationPolicy",
        arguments={
            # TODO: Map old Controller args to new CacheOptions format
            # Old: allow_heuristics, allow_stale, cacheable_methods, cacheable_status_codes
            # New: CacheOptions(shared, supported_methods, allow_stale)
        },
    )

    storage: Service = Service(
        base="hishel.AsyncBaseStorage",
        type="harp_apps.http_client.contrib.hishel.storages.AsyncStorage",
        arguments={
            "ttl": None,
            "check_ttl_every": 60.0,
        },
    )

from harp.config import Configurable, Service

# HTTP status codes that are heuristically cacheable according to RFC 9111
# Migrated from hishel 0.1.x to avoid dependency on internal APIs
HEURISTICALLY_CACHEABLE_STATUS_CODES = (200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501)


class CacheSettings(Configurable):
    #: Global cache flag, set to false to disable caching.
    enabled: bool = True

    #: Cache transport to use for the client. This is usually a hishel.AsyncCacheTransport (or subclass) instance.
    transport: Service = Service(type="hishel.AsyncCacheTransport")

    controller: Service = Service(
        type="hishel.Controller",
        arguments={
            "allow_heuristics": False,
            "allow_stale": False,
            "cacheable_methods": ["GET", "HEAD"],
            "cacheable_status_codes": list(HEURISTICALLY_CACHEABLE_STATUS_CODES),
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

from harp.config import Configurable, Service, ApplicationSettingsMixin

# HTTP status codes that are heuristically cacheable according to RFC 9111
# Migrated from hishel 0.1.x to avoid dependency on internal APIs
HEURISTICALLY_CACHEABLE_STATUS_CODES = (
    200,
    203,
    204,
    206,
    300,
    301,
    308,
    404,
    405,
    410,
    414,
    501,
)


class HttpCacheSettings(ApplicationSettingsMixin, Configurable):
    #: Cache transport to use for the client. This is usually a hishel._async_httpx.AsyncCacheTransport (or subclass) instance.
    transport: Service = Service(
        base="hishel._async_httpx.AsyncCacheTransport",
        type="harp_apps.http_cache.transports.AsyncCacheTransport",
    )

    #: Cache policy to use for determining what is cacheable.
    #: hishel 1.0 uses SpecificationPolicy with CacheOptions.
    #: Default configuration (defined in services.yml):
    #:   - shared: True (shared cache mode)
    #:   - supported_methods: ["GET", "HEAD"] (only cache GET and HEAD requests)
    #:   - allow_stale: False (do not serve stale responses)
    #:
    #: To customize cache behavior, override the entire policy service:
    #:   http_client:
    #:     cache:
    #:       policy:
    #:         type: my_custom_policy.CustomPolicy
    policy: Service = Service(type="hishel.SpecificationPolicy")

    storage: Service = Service(
        base="hishel.AsyncBaseStorage",
        type="harp_apps.http_cache.storages.AsyncStorage",
        arguments={
            "ttl": None,
            "check_ttl_every": 60.0,
        },
    )

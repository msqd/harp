from pydantic import Field, IPvAnyNetwork, model_validator

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


class CachePolicyOptions(Configurable):
    """Options of the cache policy, mapped onto ``hishel.CacheOptions``."""

    #: Behave as a shared cache (RFC 9111), as opposed to a private one.
    shared: bool = True

    #: HTTP methods whose responses can be cached.
    supported_methods: list[str] = Field(default_factory=lambda: ["GET", "HEAD"])

    #: Serve stale responses instead of refetching them.
    allow_stale: bool = False


class CachePolicySettings(Service):
    #: Options given to the policy, as a ``hishel.CacheOptions``.
    options: CachePolicyOptions = Field(default_factory=CachePolicyOptions)

    @model_validator(mode="after")
    def __reject_cache_options_argument(self):
        # SpecificationPolicy does not coerce a mapping into CacheOptions: it would load, then fail on the first request.
        if "cache_options" in (self.arguments or {}):
            raise ValueError("cache_options cannot be set as a policy argument, use http_cache.policy.options instead.")
        return self


class PurgeSettings(Configurable):
    """``PURGE`` removes one cache entry, for the peers allowed to ask."""

    #: Answer ``PURGE`` requests instead of proxying them.
    enabled: bool = False

    #: Peer addresses (IP addresses or CIDR ranges) allowed to purge. Empty by default: nobody.
    allow: list[IPvAnyNetwork] = Field(default_factory=list)


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
    #: To customize the options, use ``policy.options`` (``shared``, ``supported_methods``, ``allow_stale``).
    #: To change the policy itself, override the entire policy service:
    #:   http_cache:
    #:     policy:
    #:       type: my_custom_policy.CustomPolicy
    policy: CachePolicySettings = CachePolicySettings(type="hishel.SpecificationPolicy")

    #: Removal of single entries with the ``PURGE`` method, off by default.
    purge: PurgeSettings = Field(default_factory=PurgeSettings)

    #: Cache storage implementation, a.k.a how to store and retrieve cache data.
    #:
    #: ``allow_heuristics`` opts into RFC 9111 §4.2.2, which lets a cache invent a freshness
    #: lifetime from ``Last-Modified`` for responses the origin never declared cacheable. HARP
    #: keeps it off, as it did before hishel 1.x: the cache key is built from the request URL
    #: alone, so guessing would let responses to differently authenticated callers collide.
    storage: Service = Service(
        base="hishel.AsyncBaseStorage",
        type="harp_apps.http_cache.storages.AsyncStorage",
        arguments={
            "ttl": 86400,
            "check_ttl_every": 60.0,
            "allow_heuristics": False,
        },
    )

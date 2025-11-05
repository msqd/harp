from typing import Any

from pydantic import model_validator

from harp.config import Configurable, Service

# HTTP status codes that are heuristically cacheable according to RFC 9111
# Migrated from hishel 0.1.x to avoid dependency on internal APIs
HEURISTICALLY_CACHEABLE_STATUS_CODES = (200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501)


class CacheSettings(Configurable):
    #: Global cache flag, set to false to disable caching.
    enabled: bool = True

    #: Cache transport to use for the client. This is usually a hishel._async_httpx.AsyncCacheTransport (or subclass) instance.
    transport: Service = Service(type="hishel._async_httpx.AsyncCacheTransport")

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
        type="harp_apps.http_client.contrib.hishel.storages.AsyncStorage",
        arguments={
            "ttl": None,
            "check_ttl_every": 60.0,
        },
    )

    @model_validator(mode="before")
    @classmethod
    def _check_for_old_controller_config(cls, data: Any) -> Any:
        """Validate that users are not using the old 'controller' configuration.

        hishel 1.0 migration: 'controller' was renamed to 'policy'.
        """
        if isinstance(data, dict) and "controller" in data:
            raise ValueError(
                "The 'controller' configuration key has been removed in hishel 1.0.\n"
                "Please use 'policy' instead.\n\n"
                "Migration guide:\n"
                "  Old (hishel 0.1.x):\n"
                "    http_client:\n"
                "      cache:\n"
                "        controller:\n"
                "          type: hishel.Controller\n"
                "          arguments:\n"
                "            allow_stale: false\n"
                "            cacheable_methods: [GET, HEAD]\n\n"
                "  New (hishel 1.0):\n"
                "    http_client:\n"
                "      cache:\n"
                "        policy:\n"
                "          type: hishel.SpecificationPolicy\n"
                "          arguments:\n"
                "            cache_options:\n"
                "              shared: true\n"
                "              supported_methods: [GET, HEAD]\n"
                "              allow_stale: false\n\n"
                "Note: 'allow_heuristics' and 'cacheable_status_codes' are no longer configurable.\n"
                "      Caching behavior is now strictly RFC 9111 compliant."
            )
        return data

from functools import cached_property

from pydantic import ByteSize, Field

from harp.settings import (
    DEFAULT_CLIENT_READ_TIMEOUT,
    DEFAULT_MIN_REQUEST_BODY_RATE,
    DEFAULT_REQUEST_BODY_GRACE_PERIOD,
)
from harp.config import ApplicationSettingsMixin, Configurable, Stateful
from harp_apps.storage.constants import DEFAULT_MAX_RECORDED_BODY_SIZE

from .endpoint import Endpoint, EndpointSettings
from .remote import Remote, RemoteEndpoint, RemoteEndpointSettings, RemoteProbe, RemoteProbeSettings, RemoteSettings

__all__ = [
    "Endpoint",
    "EndpointSettings",
    "Proxy",
    "ProxySettings",
    "Remote",
    "RemoteEndpoint",
    "RemoteEndpointSettings",
    "RemoteProbe",
    "RemoteProbeSettings",
    "RemoteSettings",
    "TagsSettings",
]


class BaseProxySettings(Configurable):
    pass


class TagsSettings(Configurable):
    """Bounds on the tags a client sets with ``x-harp-*`` request headers. A tag over a bound is dropped, never the
    request."""

    #: Tags kept per transaction: the first ones in request header order.
    max_count: int = Field(20, gt=0)

    #: Longest tag name kept, in characters.
    max_name_length: int = Field(64, gt=0)

    #: Longest tag value kept, in characters.
    max_value_length: int = Field(256, gt=0)


class ProxySettings(ApplicationSettingsMixin, BaseProxySettings):
    """
    Configuration parser for ``proxy`` settings.

    .. code-block:: yaml

        endpoints:
          # see ProxyEndpoint
          - ...

    """

    endpoints: list[EndpointSettings] = []

    #: How much of a request or response body is recorded, at most: a byte count or a size with its unit (``"1MiB"``). A
    #: longer body is still sent whole, recorded truncated and marked ``truncated-request-body`` or
    #: ``truncated-response-body``; a response is also not stored in the http cache.
    max_recorded_body_size: ByteSize = Field(ByteSize(DEFAULT_MAX_RECORDED_BODY_SIZE), gt=0)

    #: Seconds a client may stay silent in the middle of a request body before it is answered ``408``, disconnected,
    #: and its request is never forwarded upstream. Each silence is timed on its own: a client sending a byte at shorter
    #: intervals is not cut (see ``min_request_body_rate``). Does not apply to a response being sent.
    client_read_timeout: float = Field(DEFAULT_CLIENT_READ_TIMEOUT, gt=0)

    #: Bytes per second (or a size with its unit: ``"1KiB"``) a request body must average once
    #: ``request_body_grace_period`` is over. A slower client is answered ``408`` and disconnected, and its request is
    #: never forwarded upstream. ``0`` disables the check.
    min_request_body_rate: ByteSize = Field(ByteSize(DEFAULT_MIN_REQUEST_BODY_RATE), ge=0)

    #: Seconds during which a request body is not held to ``min_request_body_rate``.
    request_body_grace_period: float = Field(DEFAULT_REQUEST_BODY_GRACE_PERIOD, ge=0)

    #: Bounds on the tags clients set with ``x-harp-*`` request headers.
    tags: TagsSettings = TagsSettings()


class Proxy(Stateful[ProxySettings]):
    @cached_property
    def endpoints(self) -> list[Endpoint]:
        return [Endpoint(settings=settings) for settings in self.settings.endpoints]

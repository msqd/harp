"""Request wrapper for cache key manipulation in load-balanced environments, and the tables of the SQL cache records.

WrappedRequest allows modifying specific request attributes (especially the URL) for cache key generation while
preserving the original request for actual network transmission.
"""

import uuid
from typing import Any, AsyncIterator, Iterator, Mapping, Optional

from hishel import Headers
from hishel import Request, RequestMetadata
from sqlalchemy import BigInteger, Float, ForeignKey, Index, LargeBinary, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from harp_apps.storage.models.base import Base

# Key used to store wrapped request reference in metadata
_WRAPPED_REQUEST_KEY = "_harp_wrapped_request"


class WrappedRequest(Request):
    """A request wrapper that allows selective attribute overrides while preserving the original.

    WrappedRequest extends hishel's Request class to support overriding specific attributes
    (method, url, headers, stream, metadata) while maintaining access to the original wrapped
    request. This is particularly useful for cache key normalization in load-balanced scenarios
    where different backend URLs should share the same cache entries.

    The wrapped request can be retrieved via unwrap() for actual network transmission,
    while the WrappedRequest itself (with overridden attributes) is used for cache operations.

    This class is designed to work with dataclasses.replace(), which hishel uses during
    cache revalidation to add conditional headers (If-None-Match, If-Modified-Since).
    The wrapped request reference is stored in metadata to survive replace() operations.

    Example:
        >>> original_request = Request(method="GET", url="http://backend1.local/api/users")
        >>> wrapped = WrappedRequest(original_request, url="http://normalized-endpoint/api/users")
        >>> wrapped.url  # Returns normalized URL for cache key
        "http://normalized-endpoint/api/users"
        >>> wrapped.unwrap().url  # Returns original URL for transmission
        "http://backend1.local/api/users"
    """

    def __init__(
        self,
        request: Request | None = None,
        /,
        *,
        method: str | None = None,
        url: str | None = None,
        headers: Headers | None = None,
        stream: Iterator[bytes] | AsyncIterator[bytes] | None = None,
        metadata: RequestMetadata | Mapping[str, Any] | None = None,
    ):
        """Initialize a wrapped request with optional attribute overrides.

        This constructor supports two modes:
        1. Normal mode (request provided): Wraps the given request with optional overrides
        2. Replace mode (request=None, all fields provided): Called by dataclasses.replace()

        Args:
            request: The original Request to wrap (None when called from replace())
            method: Optional method override (defaults to wrapped.method)
            url: Optional URL override (defaults to wrapped.url)
            headers: Optional headers override (defaults to wrapped.headers)
            stream: Optional stream override (defaults to wrapped.stream)
            metadata: Optional metadata override (defaults to wrapped.metadata)
        """
        if request is not None:
            # Normal construction: wrap the provided request
            # Store the wrapped request reference in metadata so it survives replace()
            merged_metadata = dict(request.metadata if metadata is None else metadata)
            merged_metadata[_WRAPPED_REQUEST_KEY] = request

            super().__init__(
                method=request.method if method is None else method,
                url=request.url if url is None else url,
                headers=request.headers if headers is None else headers,
                stream=request.stream if stream is None else stream,
                metadata=merged_metadata,
            )
        else:
            # Replace mode: called by dataclasses.replace() with all fields as kwargs
            # The wrapped request should already be in metadata from a previous wrap
            super().__init__(
                method=method,
                url=url,
                headers=headers,
                stream=stream,
                metadata=metadata,
            )

    def unwrap(self) -> Request:
        """Return the request to actually send upstream.

        The split is by who changed what. ``method`` and ``url`` come from the wrapped request,
        because those are the attributes this class overrides for cache-key normalization and
        the origin must be addressed as it really is. ``headers`` and ``stream`` are taken as
        they stand **now**, because hishel changes those.

        That second half is what makes revalidation work. hishel builds the conditional request
        with ``dataclasses.replace(request, headers={..., "if-none-match": ...})``, and
        ``replace()`` carries this object's metadata through untouched, so the wrapped request
        held in that metadata is the request as it was *before* the conditional headers existed.
        Returning it sends the revalidation with no validator at all: the origin has nothing to
        compare against, cannot answer 304, and transfers the whole body again.

        Returns:
            A plain Request addressed at the real origin, carrying the current headers and body.
        """
        wrapped = self.metadata.get(_WRAPPED_REQUEST_KEY)
        return Request(
            method=wrapped.method,
            url=wrapped.url,
            headers=self.headers,
            stream=self.stream,
            metadata=wrapped.metadata,
        )


#: The cache key, bytewise ordered so that a range of keys is an endpoint, or a path prefix under it. PostgreSQL
#: would sort it by the database collation, which is not bytewise.
_KEY = Text().with_variant(Text(collation="C"), "postgresql")


class CacheResource(Base):
    """One per cache key that holds a variant (ADR-0014). The key is the request url, its host the endpoint name."""

    __tablename__ = "http_cache_resources"
    # resources by endpoint, then path
    __table_args__ = (Index("ix_http_cache_resources_endpoint_key", "endpoint", "key"),)

    key: Mapped[str] = mapped_column(_KEY, primary_key=True)
    endpoint: Mapped[str] = mapped_column(_KEY)


class CacheBody(Base):
    """A response body, stored once whoever carries it: by the digest of its content."""

    __tablename__ = "http_cache_bodies"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)


class CacheVariant(Base):
    """One stored response of a resource, for one combination of the request headers it varies on."""

    __tablename__ = "http_cache_variants"
    __table_args__ = (
        Index("ix_http_cache_variants_stored_at", "stored_at"),
        Index("ix_http_cache_variants_body_digest", "body_digest"),
        # largest entries of an endpoint: read from the end of the index
        Index("ix_http_cache_variants_endpoint_body_size", "endpoint", "body_size"),
    )

    key: Mapped[str] = mapped_column(_KEY, ForeignKey("http_cache_resources.key"), primary_key=True)
    variant: Mapped[str] = mapped_column(String(64), primary_key=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    endpoint: Mapped[str] = mapped_column(Text)
    #: Reserved for the invalidation log (#1596): the invalidation counter read before the origin fetch.
    stamp: Mapped[int] = mapped_column(BigInteger, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger)
    vary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_digest: Mapped[str] = mapped_column(String(64), ForeignKey("http_cache_bodies.digest"))
    body_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[float] = mapped_column(Float)
    stored_at: Mapped[float] = mapped_column(Float)
    head: Mapped[bytes] = mapped_column(LargeBinary)


class CacheStats(Base):
    """What an endpoint holds, kept on write: its variants, and the bytes of their bodies."""

    __tablename__ = "http_cache_stats"

    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    entries: Mapped[int] = mapped_column(BigInteger)
    bytes: Mapped[int] = mapped_column(BigInteger)

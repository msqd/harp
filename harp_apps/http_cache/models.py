"""Request wrapper for cache key manipulation in load-balanced environments.

This module provides WrappedRequest, which allows modifying specific request attributes
(especially the URL) for cache key generation while preserving the original request
for actual network transmission.
"""

from hishel import Headers
from hishel import Request, RequestMetadata
from typing import Iterator, AsyncIterator, Mapping, Any

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
        """Return the original wrapped request.

        Returns:
            The original Request instance that was wrapped, with all its original attributes intact.
        """
        return self.metadata.get(_WRAPPED_REQUEST_KEY)

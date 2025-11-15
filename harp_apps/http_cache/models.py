"""Request wrapper for cache key manipulation in load-balanced environments.

This module provides WrappedRequest, which allows modifying specific request attributes
(especially the URL) for cache key generation while preserving the original request
for actual network transmission.
"""

from hishel import Headers
from hishel import Request, RequestMetadata
from typing import Iterator, AsyncIterator, Mapping, Any


class WrappedRequest(Request):
    """A request wrapper that allows selective attribute overrides while preserving the original.

    WrappedRequest extends hishel's Request class to support overriding specific attributes
    (method, url, headers, stream, metadata) while maintaining access to the original wrapped
    request. This is particularly useful for cache key normalization in load-balanced scenarios
    where different backend URLs should share the same cache entries.

    The wrapped request can be retrieved via unwrap() for actual network transmission,
    while the WrappedRequest itself (with overridden attributes) is used for cache operations.

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
        request: Request,
        /,
        *,
        method: str | None = None,
        url: str | None = None,
        headers: Headers | None = None,
        stream: Iterator[bytes] | AsyncIterator[bytes] | None = None,
        metadata: RequestMetadata | Mapping[str, Any] | None = None,
    ):
        """Initialize a wrapped request with optional attribute overrides.

        Args:
            request: The original Request to wrap
            method: Optional method override (defaults to wrapped.method)
            url: Optional URL override (defaults to wrapped.url)
            headers: Optional headers override (defaults to wrapped.headers)
            stream: Optional stream override (defaults to wrapped.stream)
            metadata: Optional metadata override (defaults to wrapped.metadata)
        """
        self._wrapped = request

        super().__init__(
            method=request.method if method is None else method,
            url=request.url if url is None else url,
            headers=request.headers if headers is None else headers,
            stream=request.stream if stream is None else stream,
            metadata=request.metadata if metadata is None else metadata,
        )

    def unwrap(self) -> Request:
        """Return the original wrapped request.

        Returns:
            The original Request instance that was wrapped, with all its original attributes intact.
        """
        return self._wrapped

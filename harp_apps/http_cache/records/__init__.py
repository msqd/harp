"""Where the cache keeps its records, see :class:`CacheRecords`."""

from .base import CacheRecords, EndpointStats, StoredVariant, VariantRecord, digest_of, endpoint_of
from .memory import MemoryCacheRecords

__all__ = [
    "CacheRecords",
    "EndpointStats",
    "MemoryCacheRecords",
    "StoredVariant",
    "VariantRecord",
    "digest_of",
    "endpoint_of",
]

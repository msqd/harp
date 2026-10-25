"""Where the cache keeps its records, see :class:`CacheRecords`."""

from .base import (
    Ban,
    BanKind,
    BanMode,
    CacheRecords,
    EndpointStats,
    StoredVariant,
    VariantRecord,
    ban_prefixes,
    digest_of,
    endpoint_of,
)
from .memory import MemoryCacheRecords

__all__ = [
    "Ban",
    "BanKind",
    "BanMode",
    "CacheRecords",
    "EndpointStats",
    "MemoryCacheRecords",
    "StoredVariant",
    "VariantRecord",
    "ban_prefixes",
    "digest_of",
    "endpoint_of",
]

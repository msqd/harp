"""Where the cache keeps its records, see :class:`CacheRecords`."""

from .base import (
    Ban,
    BanKind,
    BanMode,
    CacheRecords,
    EndpointStats,
    Reclaimed,
    StoredVariant,
    VariantRecord,
    ban_prefixes,
    covered_ranges,
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
    "Reclaimed",
    "StoredVariant",
    "VariantRecord",
    "ban_prefixes",
    "covered_ranges",
    "digest_of",
    "endpoint_of",
]

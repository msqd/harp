"""Blob id computation on small, medium and large bodies.

``blob_id[...]`` is `Blob.from_data` end to end, ``digest[...]`` is the digest function alone: it shows the boundary
cost (argument conversion, call) against OpenSSL's hashlib. Run once per ``HARP_NATIVE`` value and compare the files.
"""

import os
import sys

import pyperf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bench.metadata import collect  # noqa: E402
from harp.models.blobs import Blob, _blob_id  # noqa: E402

SIZES = {"64B": 64, "1KB": 1024, "100KB": 100 * 1024, "5MB": 5 * 1024 * 1024}


def blob_id(data):
    return Blob.from_data(data, content_type="application/json")


def digest(data):
    return _blob_id(data, "application/json")


runner = pyperf.Runner(metadata=collect())
for name, size in SIZES.items():
    runner.bench_func(f"blob_id[{name}]", blob_id, os.urandom(size))
    runner.bench_func(f"digest[{name}]", digest, os.urandom(size))

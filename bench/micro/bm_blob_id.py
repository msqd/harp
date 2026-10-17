"""Blob id computation (`Blob.from_data`) on small, medium and large bodies."""

import os
import sys

import pyperf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bench.metadata import collect  # noqa: E402
from harp.models.blobs import Blob  # noqa: E402

SIZES = {"1KB": 1024, "100KB": 100 * 1024, "5MB": 5 * 1024 * 1024}


def blob_id(data):
    return Blob.from_data(data, content_type="application/json")


runner = pyperf.Runner(metadata=collect())
for name, size in SIZES.items():
    runner.bench_func(f"blob_id[{name}]", blob_id, os.urandom(size))

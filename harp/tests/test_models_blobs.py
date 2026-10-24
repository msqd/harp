import threading
import hashlib

import pytest

from harp.models import Blob
from harp.models.blobs import OFFLOAD_HASH_THRESHOLD


def _expected_id(data: bytes, content_type: str | None) -> str:
    content_type_bytes = content_type.encode("utf-8") if content_type else b""
    framed = len(content_type_bytes).to_bytes(8, "big") + content_type_bytes + data
    return hashlib.sha256(framed).hexdigest()[:40]


@pytest.mark.parametrize(
    "data, content_type, expected_type",
    [
        (b"", None, None),
        (b"hello", None, None),
        ("héllo", "text/plain", "text/plain"),
        (b'{"a": 1}', "application/json; charset=utf-8", "application/json"),
        (bytes(range(256)) * 10, "http/headers", "http/headers"),
    ],
)
def test_blob_id_is_truncated_sha256_of_framed_type_and_data(data, content_type, expected_type):
    blob = Blob.from_data(data, content_type=content_type)
    assert blob.id == _expected_id(blob.data, expected_type)
    assert blob.content_type == expected_type


def test_content_type_and_body_cannot_shift_into_each_other():
    assert Blob.from_data(b"b/c\nx", content_type="a").id != Blob.from_data(b"x", content_type="a\nb/c").id
    assert Blob.from_data(b"\nx", content_type="a").id != Blob.from_data(b"x", content_type="a\n").id


def test_different_content_types_never_share_an_id():
    assert Blob.from_data(b"x", content_type="text/plain").id != Blob.from_data(b"x", content_type="text/html").id
    assert Blob.from_data(b"x").id != Blob.from_data(b"x", content_type="text/plain").id


def test_id_is_40_hex_characters():
    assert len(Blob.from_data(b"x").id) == 40


@pytest.mark.parametrize("size", [0, 10, 1 << 20])
async def test_afrom_data_matches_from_data(size):
    data = b"x" * size
    assert await Blob.afrom_data(data, content_type="text/plain") == Blob.from_data(data, content_type="text/plain")


@pytest.mark.parametrize(
    ("size", "offloaded"),
    [(OFFLOAD_HASH_THRESHOLD - 1, False), (OFFLOAD_HASH_THRESHOLD, True)],
)
async def test_afrom_data_offloads_only_large_bodies(monkeypatch, size, offloaded):
    hashing_threads = []
    from_data = Blob.from_data.__func__

    def spy(cls, *args, **kwargs):
        hashing_threads.append(threading.current_thread())
        return from_data(cls, *args, **kwargs)

    monkeypatch.setattr(Blob, "from_data", classmethod(spy))

    await Blob.afrom_data(b"x" * size)

    assert len(hashing_threads) == 1
    assert (hashing_threads[0] is not threading.main_thread()) is offloaded

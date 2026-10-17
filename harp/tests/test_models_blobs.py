import hashlib

import pytest

from harp.models import Blob


def _legacy_id(data: bytes, content_type: str | None) -> str:
    return hashlib.sha1((content_type.encode("utf-8") if content_type else b"") + b"\n" + data).hexdigest()


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
def test_blob_id_is_sha1_of_type_newline_data(data, content_type, expected_type):
    blob = Blob.from_data(data, content_type=content_type)
    assert blob.id == _legacy_id(blob.data, expected_type)
    assert blob.content_type == expected_type


@pytest.mark.parametrize("size", [0, 10, 1 << 20])
async def test_afrom_data_matches_from_data(size):
    data = b"x" * size
    assert await Blob.afrom_data(data, content_type="text/plain") == Blob.from_data(data, content_type="text/plain")

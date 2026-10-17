import os
import random
import subprocess
import sys

import pytest

from harp._native import COMPONENTS, NativeUnavailableError, core
from harp.models.blobs import blob_id_python


def _has_extension() -> bool:
    try:
        core()
    except NativeUnavailableError:
        return False
    return True


HAS_EXTENSION = _has_extension()
CONTENT_TYPES = [None, "", "text/plain", "application/json", "http/headers", "text/ünïcödé", "日本語/テスト"]
SIZES = [0, 1, 55, 56, 63, 64, 65, 1000, 65535, 65536, 65537, 1 << 20, 5 << 20]


def test_blob_id_is_a_native_component():
    assert "blob_id" in COMPONENTS


@pytest.mark.skipif(HAS_EXTENSION, reason="extension is built")
def test_requesting_native_without_extension_fails_hard():
    result = subprocess.run(
        [sys.executable, "-c", "import harp.models.blobs"],
        env={**os.environ, "HARP_NATIVE": "blob_id"},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "NativeUnavailableError" in result.stderr


@pytest.mark.skipif(not HAS_EXTENSION, reason="native extension is not built")
class TestNativeParity:
    @pytest.fixture
    def native(self):
        return core().blob_id

    @pytest.mark.parametrize("content_type", CONTENT_TYPES)
    @pytest.mark.parametrize("size", SIZES)
    def test_same_digest(self, native, size, content_type):
        data = random.Random(size).randbytes(size)
        assert native(data, content_type) == blob_id_python(data, content_type)

    def test_random_sizes(self, native):
        rng = random.Random(1174)
        for _ in range(200):
            data = rng.randbytes(rng.randint(0, 5 << 20) if rng.random() < 0.05 else rng.randint(0, 4096))
            content_type = rng.choice(CONTENT_TYPES)
            assert native(data, content_type) == blob_id_python(data, content_type)

    def test_content_type_is_optional(self, native):
        assert native(b"abc") == blob_id_python(b"abc", None)

    def test_rejects_non_bytes(self, native):
        with pytest.raises(TypeError):
            native("text", None)

    def test_lone_surrogate_content_type_raises_like_python(self, native):
        with pytest.raises(UnicodeEncodeError):
            blob_id_python(b"", "\ud800")
        with pytest.raises(UnicodeEncodeError):
            native(b"", "\ud800")

    def test_blob_from_data_uses_native_when_requested(self):
        env = {**os.environ, "HARP_NATIVE": "blob_id"}
        code = (
            "from harp.models.blobs import Blob, blob_id_python\n"
            "from harp._native import core\n"
            "import harp.models.blobs as m\n"
            "assert m._blob_id is core().blob_id\n"
            "assert Blob.from_data(b'x', content_type='a/b; c=d').id == blob_id_python(b'x', 'a/b')\n"
        )
        subprocess.run([sys.executable, "-c", code], env=env, check=True)

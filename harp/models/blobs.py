import asyncio
import dataclasses
import hashlib
import json

import orjson

from harp._native import select
from harp.utils.bytes import ensure_bytes, ensure_str

from .base import Entity


# Above this size, hashing is offloaded to a thread (hashlib releases the GIL on large buffers).
OFFLOAD_HASH_THRESHOLD = 64 * 1024


def blob_id_python(data: bytes, content_type: str | None) -> str:
    """Hex sha1 of ``content_type``, a newline, then ``data``. The native ``blob_id`` is its exact equivalent."""
    digest = hashlib.sha1(content_type.encode("utf-8") if content_type else b"")
    digest.update(b"\n")
    digest.update(data)
    return digest.hexdigest()


# Resolved once, at import: HARP_NATIVE=blob_id switches it.
_blob_id = select("blob_id", blob_id_python)


@dataclasses.dataclass(kw_only=True)
class Blob(Entity):
    id: str
    data: bytes
    content_type: str = None

    @classmethod
    def from_data(cls, data, /, *, content_type=None):
        content_type = ensure_str(content_type) if content_type else None
        if content_type and ";" in content_type:
            # xxx hack, we should parse the rest of the content type
            content_type = content_type.split(";", 1)[0].strip()

        data = ensure_bytes(data)
        return cls(id=_blob_id(data, content_type), data=data, content_type=content_type)

    @classmethod
    async def afrom_data(cls, data, /, *, content_type=None):
        """Same as `from_data`, hashing large bodies in a thread to keep the event loop responsive."""
        if len(data) < OFFLOAD_HASH_THRESHOLD:
            return cls.from_data(data, content_type=content_type)
        return await asyncio.to_thread(cls.from_data, data, content_type=content_type)

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return True

    def prettify(self):
        if self.content_type == "application/json":
            try:
                data = orjson.loads(self.data)
            except orjson.JSONDecodeError:
                try:
                    data = json.loads(self.data)
                except json.JSONDecodeError as exc:
                    raise ValueError("Could not decode json data.") from exc
            try:
                return orjson.dumps(data, option=orjson.OPT_INDENT_2)
            except orjson.JSONEncodeError:
                try:
                    return json.dumps(data, indent=4)
                except json.JSONDecodeError as exc:
                    raise ValueError("Could not encode json data.") from exc

        raise NotImplementedError(f"Cannot prettify blob of type {self.content_type}")

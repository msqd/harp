import asyncio
import dataclasses
import hashlib
import json

import orjson

from harp.utils.bytes import ensure_bytes, ensure_str

from .base import Entity


BLOB_ID_LENGTH = 40

# Above this size, hashing is offloaded to a thread (hashlib releases the GIL on large buffers).
OFFLOAD_HASH_THRESHOLD = 64 * 1024


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
        # Content type is length-framed, so no (type, body) pair can produce the hash input of another.
        # SHA-256 truncated to 160 bits keeps the 40 hex characters of the historical SHA-1 ids.
        content_type_bytes = content_type.encode("utf-8") if content_type else b""
        digest = hashlib.sha256(len(content_type_bytes).to_bytes(8, "big"))
        digest.update(content_type_bytes)
        digest.update(data)
        return cls(id=digest.hexdigest()[:BLOB_ID_LENGTH], data=data, content_type=content_type)

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

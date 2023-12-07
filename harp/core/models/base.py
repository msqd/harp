from typing import Any

from dataclasses_jsonschema import JsonSchemaMixin


class Entity(JsonSchemaMixin):
    id: Any

    def children(self):
        yield from ()

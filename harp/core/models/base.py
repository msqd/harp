from typing import Any

from dataclasses_jsonschema import JsonSchemaMixin


class Entity(JsonSchemaMixin):
    id: Any

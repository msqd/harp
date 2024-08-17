import pprint

from pydantic import BaseModel

from harp.utils.typescript import generate_schema, generate_typescript


class Settings(BaseModel):
    name: str


class Gizmo(BaseModel):
    settings: Settings


if __name__ == "__main__":
    schema = generate_schema()
    pprint.pprint(schema)
    generate_typescript(schema)

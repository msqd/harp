import os
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from orjson import orjson
from pydantic.json_schema import models_json_schema

from harp import ROOT_DIR

JSON2TS = os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend/node_modules/.bin/json2ts")
PRETTIER = os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend/node_modules/.bin/prettier")


def remove_titles_for_non_objects(schema: dict):
    if "$defs" in schema:
        for name in schema["$defs"]:
            if "properties" in schema["$defs"][name]:
                for prop in schema["$defs"][name]["properties"]:
                    if schema["$defs"][name]["properties"][prop].get("type") != "object":
                        schema["$defs"][name]["properties"][prop].pop("title", None)
    return schema


def generate_schema(models, type="serialization"):
    refs, schema = models_json_schema([(model, type) for model in models], title="__ROOT__")
    schema["anyOf"] = [ref for ref in refs.values()]
    schema = remove_titles_for_non_objects(schema)
    return schema


@contextmanager
def generate_typescript_and_jsonschema(schema, *, namespace):
    with (
        NamedTemporaryFile("wb+", delete_on_close=False) as infile,
        NamedTemporaryFile(delete_on_close=False) as outfile,
        NamedTemporaryFile(delete_on_close=False) as schema_outfile,
    ):
        infile.write(orjson.dumps(schema))
        infile.close()
        os.system(
            f"cd {ROOT_DIR}; {JSON2TS} {infile.name}"
            f" | sed '/export type __ROOT__ =/i \\\ndeclare namespace {namespace} {{\n'"
            f" | sed 's/\\(export type __ROOT__ = \\)/\\1\\n/'"
            f" | sed '/export type __ROOT__/,/;/d'"
            f" | sed '$ a \\\n }}'"
            f" | {PRETTIER} --parser typescript"
            f" > {outfile.name}"
        )
        os.system(f"cd {ROOT_DIR}; cat {infile.name} | {PRETTIER} --parser json > {schema_outfile.name}")
        yield outfile.name, schema_outfile.name

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
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
    models = sorted(models, key=lambda model: (model.__module__, model.__qualname__))
    refs, schema = models_json_schema([(model, type) for model in models], title="__ROOT__")
    schema["anyOf"] = [ref for ref in refs.values()]
    schema = remove_titles_for_non_objects(schema)
    return schema


def _run(argv, *, input=None):
    return subprocess.run(argv, input=input, cwd=ROOT_DIR, check=True, capture_output=True, text=True).stdout


@contextmanager
def generate_typescript_and_jsonschema(schema, *, namespace):
    with (
        NamedTemporaryFile("wb+", delete_on_close=False) as infile,
        NamedTemporaryFile(delete_on_close=False) as outfile,
        NamedTemporaryFile(delete_on_close=False) as schema_outfile,
    ):
        infile.write(orjson.dumps(schema))
        infile.close()

        types = _run([JSON2TS, infile.name])
        types = _run(["sed", f"/export type __ROOT__ =/i \\\ndeclare namespace {namespace} {{\n"], input=types)
        types = _run(["sed", "s/\\(export type __ROOT__ = \\)/\\1\\n/"], input=types)
        types = _run(["sed", "/export type __ROOT__/,/;/d"], input=types)
        types = _run(["sed", "$ a \\\n }"], input=types)
        Path(outfile.name).write_text(_run([PRETTIER, "--parser", "typescript"], input=types))

        with open(infile.name) as schema_in:
            Path(schema_outfile.name).write_text(_run([PRETTIER, "--parser", "json"], input=schema_in.read()))
        yield outfile.name, schema_outfile.name

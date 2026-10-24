import random
import subprocess

import pytest

from pydantic import BaseModel

from tools.typescript import generate_schema, generate_typescript_and_jsonschema


class Alpha(BaseModel):
    name: str = "a"


class Beta(BaseModel):
    alpha: Alpha | None = None


class Gamma(BaseModel):
    beta: Beta | None = None


MODELS = [Alpha, Beta, Gamma]


def test_generate_schema_does_not_depend_on_model_order():
    expected = generate_schema(MODELS)

    for seed in range(10):
        shuffled = list(MODELS)
        random.Random(seed).shuffle(shuffled)
        assert generate_schema(shuffled) == expected
        assert list(generate_schema(shuffled)["$defs"]) == list(expected["$defs"])
        assert generate_schema(shuffled)["anyOf"] == expected["anyOf"]


def test_failing_json2ts_fails_generation(monkeypatch):
    monkeypatch.setattr("tools.typescript.JSON2TS", "/bin/false")

    with pytest.raises(subprocess.CalledProcessError):
        with generate_typescript_and_jsonschema(generate_schema(MODELS), namespace="Test"):
            pass


def test_missing_json2ts_fails_generation(monkeypatch):
    monkeypatch.setattr("tools.typescript.JSON2TS", "/nonexistent/json2ts")

    with pytest.raises(FileNotFoundError):
        with generate_typescript_and_jsonschema(generate_schema(MODELS), namespace="Test"):
            pass

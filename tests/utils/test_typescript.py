import random

from pydantic import BaseModel

from harp.utils.typescript import generate_schema


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

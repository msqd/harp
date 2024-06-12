from itertools import chain
from typing import Optional


def flatten_facet_value(values: list):
    return list(
        chain(
            *map(lambda x: x.split(","), values),
        ),
    )


def str_to_float_or_none(s: str) -> Optional[float]:
    try:
        return float(s)
    except ValueError:
        return None

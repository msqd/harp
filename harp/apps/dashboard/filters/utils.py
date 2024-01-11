from itertools import chain


def flatten_facet_value(values: list):
    return list(
        chain(
            *map(lambda x: x.split(","), values),
        ),
    )

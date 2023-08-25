from typing import Any


class Entity:
    id: Any

    def children(self):
        yield from ()

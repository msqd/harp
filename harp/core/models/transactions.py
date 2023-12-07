import dataclasses
import pprint
from datetime import datetime

from harp.core.models.base import Entity


@dataclasses.dataclass(kw_only=True)
class Transaction(Entity):
    id: str
    type: str  # enum http websocket lifecycle ...
    started_at: datetime
    finished_at: datetime = None
    ellapsed: float = None


if __name__ == "__main__":
    pprint.pprint(Transaction.json_schema())

    transaction = Transaction(id="123", started_at=datetime.now(), finished_at=datetime.now(), ellapsed=0.1)

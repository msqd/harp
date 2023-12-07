import dataclasses
import pprint
from datetime import datetime

from dataclasses_jsonschema import JsonSchemaMixin


@dataclasses.dataclass
class Transaction(JsonSchemaMixin):
    id: str
    started_at: datetime
    finished_at: datetime
    ellapsed: float


if __name__ == "__main__":
    pprint.pprint(Transaction.json_schema())

    transaction = Transaction(id="123", started_at=datetime.now(), finished_at=datetime.now(), ellapsed=0.1)
    pprint.pprint(transaction.to_json())

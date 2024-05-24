import dataclasses
from datetime import date

from dataclasses_jsonschema import JsonSchemaMixin


@dataclasses.dataclass(kw_only=True)
class TransactionsByDate(JsonSchemaMixin):
    date: date
    transactions: int
    errors: int

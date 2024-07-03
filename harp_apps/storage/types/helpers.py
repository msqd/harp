from datetime import datetime
from typing import TypedDict


class TransactionsGroupedByTimeBucket(TypedDict):
    datetime: datetime
    count: int
    errors: int
    cached: int
    meanDuration: float
    meanTpdex: float

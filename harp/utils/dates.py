from datetime import date, datetime
from typing import Optional


def ensure_date(x) -> Optional[date]:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return datetime.strptime(x, "%Y-%m-%d").date()

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


def ensure_datetime(x, tz=None) -> Optional[datetime]:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.replace(tzinfo=tz)
    if isinstance(x, date):
        return datetime.combine(x, datetime.min.time(), tzinfo=tz)
    try:
        return datetime.strptime(x, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
    except ValueError:
        return datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=tz)

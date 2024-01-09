from datetime import date, datetime


def ensure_date(x):
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return datetime.strptime(x, "%Y-%m-%d").date()

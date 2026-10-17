from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from .conftest import http_date, make_cacheable_response


def test_make_cacheable_response_dates_the_response_now_by_default():
    response = make_cacheable_response()

    age = datetime.now(timezone.utc) - parsedate_to_datetime(response.headers["date"])
    assert timedelta(0) <= age < timedelta(seconds=5)


def test_make_cacheable_response_date_is_overridable():
    date = http_date(delta=timedelta(hours=-1))

    assert make_cacheable_response(date=date).headers["date"] == date

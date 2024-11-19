from decimal import Decimal

from pydantic import HttpUrl

from harp.views.json import serialize


def test_decimal_serialization():
    decimal = Decimal("3.14")
    assert serialize(decimal) == b'"3.14"'


def test_url_serialization():
    url = HttpUrl("https://example.com")
    assert serialize(url) == b'"https://example.com/"'

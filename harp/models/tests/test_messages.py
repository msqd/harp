from unittest.mock import ANY

from harp.models.request import DeprecatedOldTransactionRequest
from harp.models.response import DeprecatedOldTransactionResponse


def test_request():
    request = DeprecatedOldTransactionRequest(headers=(), content=b"", method="GET", url="http://example.com")
    assert request.normalize() == b"HTTP GET http://example.com\n\n\n"
    assert request.asdict() == {
        "id": ANY,
        "method": "GET",
        "url": "http://example.com",
    }


def test_response():
    response = DeprecatedOldTransactionResponse(headers=(), content=b"", status_code=200)
    assert response.normalize() == b"HTTP/1.1 200\n\n\n"
    assert response.asdict() == {
        "id": ANY,
        "statusCode": 200,
    }

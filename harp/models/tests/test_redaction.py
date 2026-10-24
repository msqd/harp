import json
from datetime import UTC, datetime

from multidict import CIMultiDict, MultiDict

from harp.http import HttpRequest, HttpResponse
from harp.http.serializers import HttpRequestSerializer, HttpResponseSerializer
from harp.models import Transaction
from harp.models.redaction import REDACTED, Redaction


def _transaction() -> Transaction:
    return Transaction(type="http", started_at=datetime.now(UTC))


class TestRedactionSet:
    def test_default_holds_the_four_credential_headers_and_no_query_parameter(self):
        redaction = Redaction()
        assert redaction.headers == {"authorization", "proxy-authorization", "cookie", "set-cookie"}
        assert redaction.query == set()

    def test_header_names_are_normalised_to_lower_case(self):
        redaction = Redaction()
        redaction.headers.add("X-Api-Key")
        assert "x-api-key" in redaction.headers
        assert "X-API-KEY" in redaction.headers
        redaction.headers.discard("Authorization")
        assert "authorization" not in redaction.headers

    def test_query_names_keep_their_case(self):
        redaction = Redaction()
        redaction.query.add("Client_Secret")
        assert "client_secret" not in redaction.query
        assert "Client_Secret" in redaction.query

    def test_each_transaction_has_its_own_set(self):
        first, second = _transaction(), _transaction()
        first.redaction.headers.add("x-api-key")
        assert "x-api-key" not in second.redaction.headers

    def test_transaction_dict_does_not_carry_the_set(self):
        transaction = _transaction()
        assert "redaction" not in transaction.as_storable_dict()
        assert "redaction" not in transaction._asdict()

    def test_dashboard_dict_is_json_serialisable_without_redaction(self):
        data = _transaction().to_dict()
        assert "redaction" not in data
        json.dumps(data)

    def test_json_schema_is_json_serialisable_without_redaction(self):
        schema = Transaction.json_schema()
        assert "redaction" not in schema["properties"]
        json.dumps(schema)


class TestRequestSerializer:
    def test_credential_headers_are_replaced_whole_by_default(self):
        request = HttpRequest(method="GET", path="/", headers={"Authorization": "Bearer xyz", "accept": "*/*"})
        headers = HttpRequestSerializer(request, Redaction()).headers
        assert headers == f"Authorization: {REDACTED}\naccept: */*"

    def test_every_occurrence_of_a_header_is_replaced(self):
        request = HttpRequest(method="GET", path="/")
        request.headers = CIMultiDict([("Cookie", "a=1"), ("cookie", "b=2")])
        assert HttpRequestSerializer(request, Redaction()).headers == f"Cookie: {REDACTED}\ncookie: {REDACTED}"

    def test_no_redaction_given_means_values_are_kept(self):
        request = HttpRequest(method="GET", path="/", headers={"Authorization": "Bearer xyz"})
        assert HttpRequestSerializer(request).headers == "Authorization: Bearer xyz"

    def test_named_query_parameters_are_redacted_in_every_occurrence(self):
        redaction = Redaction()
        redaction.query.add("client_secret")
        request = HttpRequest(method="GET", path="/oauth/token")
        request.query = MultiDict([("client_secret", "a"), ("x", "1"), ("client_secret", "b")])
        summary = HttpRequestSerializer(request, redaction).summary
        assert summary == f"GET /oauth/token?client_secret={REDACTED}&x=1&client_secret={REDACTED} HTTP/1.1"

    def test_query_is_untouched_by_default(self):
        request = HttpRequest(method="GET", path="/")
        request.query = MultiDict([("token", "abc")])
        assert HttpRequestSerializer(request, Redaction()).summary == "GET /?token=abc HTTP/1.1"

    def test_serializing_does_not_change_the_message(self):
        request = HttpRequest(method="GET", path="/", headers={"Authorization": "Bearer xyz"})
        HttpRequestSerializer(request, Redaction()).headers
        assert request.headers["authorization"] == "Bearer xyz"


class TestResponseSerializer:
    def test_set_cookie_is_redacted(self):
        response = HttpResponse(b"", headers={"Set-Cookie": "sid=1; HttpOnly", "etag": '"a"'})
        assert HttpResponseSerializer(response, Redaction()).headers == f'Set-Cookie: {REDACTED}\netag: "a"'

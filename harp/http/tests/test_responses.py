from httpx import ByteStream

from harp.http import HttpResponse


class BaseHttpResponseTest:
    """
    Base class for testing HTTP responses.
    """

    ResponseType = HttpResponse

    def create_response(self, body, **kwargs) -> HttpResponse:
        return self.ResponseType(body, **kwargs)


class TestHttpResponseStatus(BaseHttpResponseTest):
    """
    Test status-related stuff on HTTP responses.
    """

    def test_default(self):
        response = self.create_response(body=b"")
        assert response.status == 200

    def test_custom_status(self):
        response = self.create_response(body=b"", status=404)
        assert response.status == 404


class TestHttpResponseHeaders(BaseHttpResponseTest):
    """
    Test headers-related stuff on HTTP responses.
    """

    def test_headers(self):
        response = self.create_response(
            body=b"",
            headers={
                "content-type": "application/json",
                "x-custom-header": "value",
            },
        )

        assert response.headers == {
            "content-type": "application/json",
            "x-custom-header": "value",
        }

    def test_content_type(self):
        response = self.create_response(body=b"", content_type="application/json")
        assert response.content_type == "application/json"


class TestHttpResponseBody(BaseHttpResponseTest):
    async def test_body_empty(self):
        response = self.create_response(body=b"")
        await response.aread()
        assert response.body == b""

    async def test_body_one_chunk(self):
        response = self.create_response(body=b"foobar")
        await response.aread()
        assert response.body == b"foobar"

    async def test_body_can_be_read_more_than_once(self):
        response = self.create_response(body=b"foobar")
        await response.aread()
        await response.aread()
        await response.aread()
        assert response.body == b"foobar"

    async def test_stream_can_be_accessed_before_reading_body(self):
        response = self.create_response(body=b"foobarbaz")
        assert [chunk async for chunk in response.stream] == [b"foobarbaz"]
        response.stream = ByteStream(b"foobarbaz")
        await response.aread()
        assert response.body == b"foobarbaz"

    async def test_stream_can_be_accessed_after_reading_body(self):
        response = self.create_response(body=b"foobarbaz")
        await response.aread()
        assert [chunk async for chunk in response.stream] == [b"foobarbaz"]
        assert response.body == b"foobarbaz"
        assert isinstance(response.body, bytes)
        assert isinstance(response.stream, ByteStream)

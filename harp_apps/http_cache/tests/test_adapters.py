"""An entry, described as the records the cache stores, and read back."""

import uuid

from hishel import Entry, EntryMeta, Headers, Request, Response
from hishel._core.models import AnyIterable

from harp.models.redaction import REDACTED, Redaction
from harp_apps.http_cache.adapters import to_entry, to_record, variant_of
from harp_apps.http_cache.records import StoredVariant, digest_of

KEY = "http://api/items?page=2"


def make_entry(*, request_headers=None, response_headers=None, body=b"payload", metadata=None) -> Entry:
    return Entry(
        id=uuid.uuid4(),
        request=Request(method="GET", url=KEY, headers=Headers(request_headers or {})),
        response=Response(
            status_code=200,
            headers=Headers({"cache-control": "max-age=60", **(response_headers or {})}),
            stream=AnyIterable(body),
            metadata=metadata or {},
        ),
        meta=EntryMeta(created_at=1700000000.5, deleted_at=None),
        cache_key=KEY.encode(),
        extra={"number_of_uses": 3},
    )


async def round_trip(entry: Entry, **kwargs) -> Entry:
    record, body = await to_record(entry, **kwargs)
    return to_entry(StoredVariant(record, body))


async def test_a_record_describes_the_entry():
    entry = make_entry(response_headers={"vary": "Accept, Accept-Encoding"}, body=b"12345")

    record, body = await to_record(entry)

    assert (record.key, record.endpoint, record.entry_id) == (KEY, "api", entry.id)
    assert (record.status, record.vary, record.body_size, record.created_at) == (
        200,
        "accept, accept-encoding",
        5,
        1700000000.5,
    )
    assert body == b"12345"
    assert record.body_digest == digest_of(b"12345")
    assert record.stamp == 0


async def test_the_stamp_is_the_one_given():
    record, _ = await to_record(make_entry(), stamp=7)

    assert record.stamp == 7


async def test_a_response_that_does_not_vary_has_no_variant():
    record, _ = await to_record(make_entry())

    assert (record.variant, record.vary) == ("", None)


async def test_a_variant_is_told_by_the_values_of_the_headers_the_response_varies_on():
    html, _ = await to_record(make_entry(request_headers={"accept": "text/html"}, response_headers={"vary": "Accept"}))
    again, _ = await to_record(make_entry(request_headers={"accept": "text/html"}, response_headers={"vary": "Accept"}))
    json, _ = await to_record(
        make_entry(request_headers={"accept": "application/json"}, response_headers={"vary": "Accept"})
    )

    assert html.variant == again.variant != json.variant
    assert variant_of({}) == ""


async def test_the_entry_is_read_back_as_stored():
    entry = make_entry(
        request_headers={"accept": "*/*", "x-name": "é"},
        response_headers={"content-type": "text/plain", "date": "Wed, 21 Oct 2015 07:28:00 GMT", "etag": '"v1"'},
        metadata={"http_version": b"HTTP/1.1", "reason_phrase": b"OK", "unknown": b"dropped"},
    )

    read = await round_trip(entry)

    assert read.id == entry.id
    assert read.cache_key == entry.cache_key
    assert (read.request.method, read.request.url) == ("GET", KEY)
    assert dict(read.request.headers) == {"accept": "*/*", "x-name": "é"}
    assert dict(read.response.headers) == dict(entry.response.headers)
    assert await read.response.aread() == b"payload"
    assert read.response.status_code == 200
    assert read.response.metadata == {"http_version": b"HTTP/1.1", "reason_phrase": b"OK"}
    assert read.meta == EntryMeta(created_at=1700000000.5, deleted_at=None)
    assert read.extra["number_of_uses"] == 3


async def test_the_entry_remembers_when_it_was_stored():
    record, body = await to_record(make_entry())

    assert to_entry(StoredVariant(record, body)).extra["stored_at"] == record.stored_at


async def test_redacted_request_headers_are_not_stored():
    entry = make_entry(request_headers={"authorization": "Bearer secret-token", "accept": "*/*"})

    record, _ = await to_record(entry, Redaction())

    assert b"secret-token" not in record.head
    assert (await round_trip(entry, redaction=Redaction())).request.headers["authorization"] == REDACTED

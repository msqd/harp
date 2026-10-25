"""The cache key: endpoint and path in clear, then a hash of the query (ADR-0014, ADR-0009)."""

import hashlib

import httpx
import pytest
from hishel import Request, SpecificationPolicy

from harp_apps.http_cache.records import MemoryCacheRecords, endpoint_of
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport


def make_transport() -> AsyncCacheTransport:
    return AsyncCacheTransport(
        next_transport=httpx.AsyncHTTPTransport(),
        policy=SpecificationPolicy(),
        storage=AsyncStorage(MemoryCacheRecords()),
    )


@pytest.fixture
def transport():
    return make_transport()


async def test_a_path_without_a_query_is_the_key(transport):
    assert await transport._get_key_for_request(Request(method="GET", url="http://api/items/1")) == "http://api/items/1"


async def test_the_query_is_only_in_the_key_as_a_hash(transport):
    key = await transport._get_key_for_request(Request(method="GET", url="http://api/items?token=s3cr3t&page=2"))

    assert key == f"http://api/items?{hashlib.sha256(b'token=s3cr3t&page=2').hexdigest()}"
    assert "s3cr3t" not in key


async def test_two_query_values_have_two_keys(transport):
    one = await transport._get_key_for_request(Request(method="GET", url="http://api/items?token=one"))
    two = await transport._get_key_for_request(Request(method="GET", url="http://api/items?token=two"))

    assert one != two
    assert one.partition("?")[0] == two.partition("?")[0]


async def test_a_request_keyed_by_its_body_still_has_its_endpoint_and_path():
    transport = make_transport()

    keys = [
        await transport._get_key_for_request(
            Request(method="POST", url="http://api/search", stream=body, metadata={"hishel_body_key": True})
        )
        for body in (httpx.ByteStream(b"one"), httpx.ByteStream(b"two"))
    ]

    assert {key.partition("?")[0] for key in keys} == {"http://api/search"}
    assert keys[0] != keys[1]
    assert endpoint_of(keys[0]) == "api"

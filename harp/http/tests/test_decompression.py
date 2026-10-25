import gzip
import zlib

import httpx
import pytest

from harp.http.decompression import MAX_CODINGS, MAX_DECODED_STEP, BoundedDecoder


def decode_all(encoding, data, *, step=MAX_DECODED_STEP):
    decoder = BoundedDecoder(encoding, step=step)
    return [*decoder.decode(data), *decoder.flush()]


def test_a_gzip_bomb_comes_out_in_bounded_pieces():
    pieces = decode_all("gzip", gzip.compress(b"0" * 1_000_000), step=4096)

    assert max(map(len, pieces)) <= 4096
    assert b"".join(pieces) == b"0" * 1_000_000


def test_the_input_may_arrive_in_arbitrary_chunks():
    encoded = gzip.compress(bytes(range(256)) * 1000)
    decoder = BoundedDecoder("gzip", step=1000)
    pieces = []
    for index in range(0, len(encoded), 7):
        pieces += decoder.decode(encoded[index : index + 7])
    pieces += decoder.flush()

    assert b"".join(pieces) == bytes(range(256)) * 1000


@pytest.mark.parametrize("wbits", [zlib.MAX_WBITS, -zlib.MAX_WBITS], ids=["zlib", "raw"])
def test_deflate_comes_in_both_flavours(wbits):
    compressor = zlib.compressobj(wbits=wbits)
    encoded = compressor.compress(b"abc" * 10_000) + compressor.flush()

    pieces = decode_all("deflate", encoded, step=1000)

    assert max(map(len, pieces)) <= 1000
    assert b"".join(pieces) == b"abc" * 10_000


def test_stacked_encodings_are_each_bounded():
    encoded = gzip.compress(gzip.compress(b"0" * 500_000))

    pieces = decode_all("gzip, gzip", encoded, step=2048)

    assert max(map(len, pieces)) <= 2048
    assert b"".join(pieces) == b"0" * 500_000


@pytest.mark.parametrize("encoding", [None, "", "identity"])
def test_no_encoding_passes_through(encoding):
    assert decode_all(encoding, b"plain") == [b"plain"]


def test_corrupt_data_is_a_decoding_error():
    with pytest.raises(httpx.DecodingError):
        decode_all("gzip", b"definitely not gzip")


def stacked(layers, body=b"payload"):
    for _ in range(layers):
        body = gzip.compress(body)
    return ", ".join(["gzip"] * layers), body


def test_four_stacked_encodings_are_decoded():
    encoding, encoded = stacked(MAX_CODINGS)

    assert b"".join(decode_all(encoding, encoded)) == b"payload"


def test_more_than_four_stacked_encodings_are_a_decoding_error():
    encoding, encoded = stacked(MAX_CODINGS + 1)

    with pytest.raises(httpx.DecodingError):
        decode_all(encoding, encoded)


def test_a_huge_number_of_encodings_is_a_decoding_error_not_a_recursion_error():
    encoding, encoded = stacked(1200)

    with pytest.raises(httpx.DecodingError):
        decode_all(encoding, encoded)


@pytest.mark.parametrize(
    "encoding, rejected",
    [
        ("gzip, , gzip,, gzip, gzip,", False),
        (" GZip ,  GZIP,gzip , Gzip", False),
        ("gzip, gzip, gzip, gzip, identity", True),
        ("identity, identity, identity, identity, identity", True),
        ("gzip, gzip, gzip, gzip, , ", False),
    ],
)
def test_codings_are_counted_after_normalising(encoding, rejected):
    decoder = BoundedDecoder(encoding)

    if rejected:
        with pytest.raises(httpx.DecodingError):
            list(decoder.decode(b""))
    else:
        assert list(decoder.decode(b"")) == []

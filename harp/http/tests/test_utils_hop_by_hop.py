from multidict import CIMultiDict

from harp.http.utils import hop_by_hop_names


def test_every_connection_header_line_names_hop_by_hop_fields():
    headers = CIMultiDict([("Connection", "keep-alive"), ("Connection", "X-Internal")])

    assert {"keep-alive", "x-internal"} <= hop_by_hop_names(headers)

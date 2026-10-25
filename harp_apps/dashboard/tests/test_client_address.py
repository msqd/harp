from ipaddress import ip_network

import pytest

from harp.http import HttpRequest
from harp_apps.dashboard.security.addresses import client_address

PROXIES = [ip_network("10.0.0.0/8"), ip_network("fd00::/8")]


def request(peer, forwarded=None):
    headers = {} if forwarded is None else {"x-forwarded-for": forwarded}
    return HttpRequest(client_ipaddr=peer, headers=headers)


def test_without_trusted_proxies_the_address_is_the_peer_whatever_the_header_says():
    assert client_address(request("203.0.113.7", "198.51.100.1"), []) == "203.0.113.7"


def test_a_peer_that_is_not_trusted_cannot_name_the_client():
    assert client_address(request("203.0.113.7", "198.51.100.1"), PROXIES) == "203.0.113.7"


def test_behind_a_trusted_proxy_the_address_is_the_one_it_saw():
    assert client_address(request("10.1.2.3", "198.51.100.1"), PROXIES) == "198.51.100.1"


def test_the_chain_is_read_from_the_right_and_stops_at_the_first_address_that_is_not_trusted():
    # the client wrote the first one; the proxies appended the others
    assert client_address(request("10.1.2.3", "6.6.6.6, 198.51.100.1, 10.9.9.9"), PROXIES) == "198.51.100.1"


def test_several_headers_are_one_chain():
    headers = {"x-forwarded-for": "6.6.6.6"}
    req = HttpRequest(client_ipaddr="10.1.2.3", headers=headers)
    req.headers.add("x-forwarded-for", "198.51.100.1")

    assert client_address(req, PROXIES) == "198.51.100.1"


@pytest.mark.parametrize("forwarded", [None, "", "not an address", "  ,  "])
def test_a_trusted_proxy_that_says_nothing_usable_stands_for_the_client(forwarded):
    assert client_address(request("10.1.2.3", forwarded), PROXIES) == "10.1.2.3"


def test_a_garbage_entry_on_the_right_is_not_skipped_to_reach_a_forged_one_on_the_left():
    assert client_address(request("10.1.2.3", "6.6.6.6, garbage"), PROXIES) == "10.1.2.3"


def test_ipv6_is_handled():
    assert client_address(request("fd00::1", "2001:db8::5"), PROXIES) == "2001:db8::5"


def test_a_chain_of_trusted_proxies_only_falls_back_to_the_peer():
    assert client_address(request("10.1.2.3", "10.4.4.4, 10.5.5.5"), PROXIES) == "10.1.2.3"


def test_an_unknown_peer_is_untrusted():
    assert client_address(request(None, "198.51.100.1"), PROXIES) == "unknown"

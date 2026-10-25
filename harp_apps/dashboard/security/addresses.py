"""The address a request comes from, for the limits on sign-in.

Behind a reverse proxy every connection comes from the proxy, so a limit per address would be a limit on everybody at once.
``dashboard.trusted_proxies`` lists the networks of the proxies HARP may believe; only a connection from one of them is
allowed to say, in ``X-Forwarded-For``, who the client was. The chain is read from the right, the proxies' end, and stops at
the first address that is not a trusted proxy: what is further left was written by the client.
"""

from ipaddress import IPv4Network, IPv6Network, ip_address
from typing import Sequence

from harp.http import HttpRequest

UNKNOWN = "unknown"


def _is_trusted(address: str, trusted: Sequence[IPv4Network | IPv6Network]) -> bool:
    try:
        parsed = ip_address(address)
    except ValueError:
        return False
    return any(parsed in network for network in trusted if parsed.version == network.version)


def client_address(request: HttpRequest, trusted: Sequence[IPv4Network | IPv6Network]) -> str:
    peer = request.client_ipaddr
    if peer is None:
        return UNKNOWN
    if not trusted or not _is_trusted(peer, trusted):
        return peer
    chain = [part.strip() for header in request.headers.getall("x-forwarded-for", []) for part in header.split(",")]
    for entry in reversed([part for part in chain if part]):
        try:
            ip_address(entry)
        except ValueError:
            return peer  # a chain that cannot be read is not read further
        if not _is_trusted(entry, trusted):
            return entry
    return peer

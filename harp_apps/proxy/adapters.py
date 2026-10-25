import time
from base64 import b64encode
from ipaddress import IPv4Network, IPv6Address, IPv6Network, ip_address
from typing import Any, Dict, Optional, Sequence
from urllib.parse import unquote, urlparse

from httpx import AsyncClient, Request, Response

from harp import __parsed_version__
from harp.http import HttpRequest
from harp.http.utils import hop_by_hop_names
from harp.models import Transaction
from harp.utils.bytes import HEADER_ENCODING, header_bytes


def strip_credentials(url: str) -> str:
    """The url without its ``user:password@`` part, safe to log and record."""
    parsed_url = urlparse(url)
    return parsed_url._replace(netloc=parsed_url.netloc.rpartition("@")[2]).geturl()


FORWARDING_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip")


def forwarding_headers(
    headers: list[tuple[str, str]], peer: str | None, trusted_proxies: Sequence[IPv4Network | IPv6Network]
) -> list[tuple[str, str]]:
    """
    The outgoing headers with the forwarding ones (``X-Forwarded-For``, ``Forwarded``, ``X-Real-IP``) made safe to
    trust: the peer's own values are dropped unless it is in ``trusted_proxies``, then the peer address is appended to
    ``X-Forwarded-For`` and ``Forwarded``. An unknown peer is untrusted and appended nowhere.
    """
    try:
        address = ip_address(peer) if peer else None
    except ValueError:
        address = None
    if isinstance(address, IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    trusted = address is not None and any(address in network for network in trusted_proxies)

    kept = [(name, value) for name, value in headers if name.lower() not in FORWARDING_HEADERS]
    inherited = {
        header: [value for name, value in headers if name.lower() == header and value.strip()]
        for header in FORWARDING_HEADERS
    }
    if trusted:
        kept += [("x-real-ip", value) for value in inherited["x-real-ip"]]
    if address is None:
        return kept

    previous = lambda header: inherited[header] if trusted else []  # noqa: E731
    forwarded_for = f'"[{address}]"' if address.version == 6 else str(address)
    kept.append(("x-forwarded-for", ", ".join([*previous("x-forwarded-for"), str(address)])))
    kept.append(("forwarded", ", ".join([*previous("forwarded"), f"for={forwarded_for}"])))
    return kept


class HttpClientProxyAdapter:
    user_agent: Optional[str] = None
    """User agent to use when proxying requests (will default to harp/<version>)."""

    def __init__(
        self,
        http_client: AsyncClient,
        *,
        extensions: Optional[Dict[str, Any]] = None,
        trusted_proxies: Sequence[IPv4Network | IPv6Network] = (),
    ):
        self.http_client = http_client
        self.trusted_proxies = tuple(trusted_proxies)
        self.user_agent = self.user_agent or self._get_default_user_agent()
        self.extensions = extensions or {}

    async def send(self, request: HttpRequest, url: str, *, transaction: Optional[Transaction] = None) -> Response:
        """
        Send the HTTP request using the provided URL.

        :param request: The HttpRequest object to be sent.
        :param url: The URL to which the request is sent.
        :param transaction: The transaction the request belongs to, whose redaction and markers the cache applies.
        :return: The HTTP response received, its body not read yet: the caller reads it, then closes it.
        """
        request = self._build_request(request, url, transaction=transaction)
        response = await self.http_client.send(request, stream=True)
        response.headers.encoding = HEADER_ENCODING  # obs-text must read back as the bytes it was

        # Add cache debugging headers if caching is being used
        if response.extensions.get("hishel_from_cache"):
            response.headers["X-Cache"] = "HIT"
            # Add Age header for cached responses
            created_at = response.extensions.get("hishel_created_at")
            if created_at is not None:
                age = int(time.time() - created_at)
                response.headers["Age"] = str(age)
        elif "hishel_from_cache" in response.extensions:
            # hishel is present but response is not from cache
            response.headers["X-Cache"] = "MISS"

        return response

    def _get_default_user_agent(self) -> str:
        """
        Get the default user agent string.

        :return: The default user agent string.
        """
        try:
            return f"harp/{__parsed_version__.major}.{__parsed_version__.minor}"
        except AttributeError:
            return "harp"

    def _get_updated_headers(self, request: HttpRequest, *, url: str) -> list:
        """
        Update the headers for the request.

        :param request: The HttpRequest object.
        :param url: The URL to which the request is sent.
        :return: A list of updated headers.
        """
        parsed_url = urlparse(url)
        request.headers["host"] = parsed_url.netloc.rpartition("@")[2]
        if self.user_agent:
            request.headers["user-agent"] = self.user_agent
        dropped = hop_by_hop_names(request.headers)
        headers = [(name, value) for name, value in request.headers.items() if name.lower() not in dropped]
        # Endpoint credentials are a fallback: any Authorization already on the request wins. Added to the
        # outgoing list only, so they never land on the recorded request.
        if parsed_url.username is not None and "authorization" not in request.headers:
            credentials = f"{unquote(parsed_url.username)}:{unquote(parsed_url.password or '')}"
            headers.append(("authorization", "Basic " + b64encode(credentials.encode()).decode()))
        return forwarding_headers(headers, request.client_ipaddr, self.trusted_proxies)

    @staticmethod
    def _transaction_extensions(transaction: Optional[Transaction]) -> Dict[str, Any]:
        """What the cache, which sits below the transaction, needs from it: read when the request is sent, after the
        rules ran."""
        if transaction is None:
            return {}
        return {"redaction": transaction.redaction, "markers": frozenset(transaction.markers)}

    def _build_request(self, request: HttpRequest, url: str, *, transaction: Optional[Transaction] = None) -> Request:
        """
        Build the HTTP request.

        :param request: The HttpRequest object.
        :param url: The URL to which the request is sent.
        :return: The built HTTP request.
        """
        headers = self._get_updated_headers(request, url=url)

        # Credentials travel in the Authorization header built above. Left in the url, httpx would override
        # that header with its own and the url would be recorded with the secret.
        remote_request = self.http_client.build_request(
            request.method,
            strip_credentials(url),
            headers=[(header_bytes(name), header_bytes(value)) for name, value in headers],
            content=request.body,
            extensions={
                "harp": {
                    **self.extensions,
                    **self._transaction_extensions(transaction),
                    # The peer HARP is talking to, never a forwarded header: the cache's PURGE allow-list reads it.
                    "client_ip": request.client_ipaddr,
                }
            },
        )

        request.extensions["remote_method"] = remote_request.method
        request.extensions["remote_url"] = str(remote_request.url)
        return remote_request

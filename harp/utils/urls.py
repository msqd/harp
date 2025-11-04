from typing import Union
from urllib.parse import urlparse, urlunparse

import httpcore


def extract_hostname_from_url(url):
    return urlparse(url).hostname


def _convert_url_to_string(url: Union[httpcore.URL, str, bytes]) -> str:
    """Convert httpcore.URL, str, or bytes to a string URL.

    Migrated from hishel._utils.normalized_url which was removed in 1.0.
    """
    if isinstance(url, httpcore.URL):
        # Convert httpcore.URL to string: scheme://host[:port]/path[?query][#fragment]
        url_str = f"{url.scheme.decode('ascii')}://{url.host.decode('ascii')}"
        if url.port is not None:
            url_str += f":{url.port}"
        if url.target:
            url_str += url.target.decode("ascii")
        return url_str
    elif isinstance(url, bytes):
        return url.decode("ascii")
    return url


def normalize_url(url: Union[httpcore.URL, str, bytes]) -> str:
    url = _convert_url_to_string(url)

    parsed_url = urlparse(url)

    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid URL: Missing scheme or netloc.")

    return urlunparse(
        parsed_url._replace(
            scheme=parsed_url.scheme.lower(),
            netloc=parsed_url.netloc.lower(),
            path=parsed_url.path or "/",
        )
    )

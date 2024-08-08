from typing import Union
from urllib.parse import urlparse, urlunparse

import httpcore
from hishel._utils import normalized_url as _normalize_url


def extract_hostname_from_url(url):
    return urlparse(url).hostname


def normalize_url(url: Union[httpcore.URL, str, bytes]) -> str:
    url = _normalize_url(url)

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

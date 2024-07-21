from urllib.parse import urlparse, urlunparse


def extract_hostname_from_url(url):
    return urlparse(url).hostname


def validate_url(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid URL: Missing scheme or netloc.")
    normalized_url = parsed_url._replace(scheme=parsed_url.scheme.lower(), netloc=parsed_url.netloc.lower())
    return urlunparse(normalized_url)

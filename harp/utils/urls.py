from urllib.parse import urlparse


def extract_hostname_from_url(url):
    return urlparse(url).hostname

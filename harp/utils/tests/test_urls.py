from ..urls import extract_hostname_from_url, normalize_url


def test_extract_hostname_from_url():
    assert extract_hostname_from_url("https://www.google.com/") == "www.google.com"
    assert extract_hostname_from_url("https://example.com:1234/") == "example.com"


def test_normalize_url():
    assert normalize_url("https://www.google.com/") == "https://www.google.com/"
    assert normalize_url("https://www.google.com") == "https://www.google.com/"
    assert normalize_url("Https://WWW.GOOGLE.COM") == "https://www.google.com/"
    assert normalize_url("http://example.com/foo/bar/baz") == "http://example.com/foo/bar/baz"

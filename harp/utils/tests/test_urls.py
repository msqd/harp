from harp.utils.urls import extract_hostname_from_url


def test_extract_hostname_from_url():
    assert extract_hostname_from_url("https://www.google.com/") == "www.google.com"
    assert extract_hostname_from_url("https://example.com:1234/") == "example.com"

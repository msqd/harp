import pytest

from harp.security.credentials import (
    SESSION_COOKIE_NAMES,
    build_token,
    generate_token,
    is_harp_token,
    strip_harp_credentials,
)

TOKEN = build_token("abcdefgh", "Z" * 43)


def test_random_tokens_are_valid_and_distinct():
    tokens = {generate_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(is_harp_token(token) for token in tokens)


def test_generated_token_has_the_documented_shape():
    assert TOKEN.startswith("harp_")
    assert len(TOKEN) == 5 + 8 + 43 + 6
    assert "_" not in TOKEN[5:]
    assert is_harp_token(TOKEN)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "harp_",
        "Bearer " + TOKEN,
        TOKEN[:-1],
        TOKEN + "a",
        "other_" + TOKEN[5:],
        TOKEN[:-1] + ("0" if TOKEN[-1] != "0" else "1"),  # typo: the checksum rejects it
        TOKEN[:10] + "-" + TOKEN[11:],  # not base62
    ],
)
def test_is_harp_token_rejects(value):
    assert not is_harp_token(value)


def test_session_cookie_names():
    assert SESSION_COOKIE_NAMES == ("__Host-harp_session", "harp_session")


def test_strip_session_cookies_keeps_the_others():
    headers = [("cookie", "a=1; __Host-harp_session=x; harp_session=y; b=2")]
    assert strip_harp_credentials(headers) == ([("cookie", "a=1; b=2")], True)


def test_strip_drops_an_emptied_cookie_header():
    headers = [("host", "h"), ("Cookie", "harp_session=y")]
    assert strip_harp_credentials(headers) == ([("host", "h")], True)


def test_strip_harp_bearer():
    headers = [("authorization", f"Bearer {TOKEN}"), ("x", "y")]
    assert strip_harp_credentials(headers) == ([("x", "y")], True)


def test_non_harp_bearer_is_forwarded_unchanged():
    headers = [("authorization", "Bearer abc.def"), ("authorization-x", "1"), ("cookie", "a=1")]
    assert strip_harp_credentials(headers) == (headers, False)


def test_non_bearer_authorization_is_kept():
    headers = [("authorization", f"Basic {TOKEN}")]
    assert strip_harp_credentials(headers) == (headers, False)


def test_bearer_scheme_is_case_insensitive():
    assert strip_harp_credentials([("Authorization", f"bearer {TOKEN}")]) == ([], True)


def test_nothing_to_strip():
    headers = [("cookie", "a=1; b=2")]
    assert strip_harp_credentials(headers) == (headers, False)


def test_header_names_are_case_insensitive():
    headers = [("AUTHORIZATION", f"Bearer {TOKEN}"), ("COOKIE", "harp_session=y")]
    assert strip_harp_credentials(headers) == ([], True)


def test_every_cookie_header_is_stripped():
    headers = [("cookie", "harp_session=y; a=1"), ("cookie", "b=2; __Host-harp_session=z")]
    assert strip_harp_credentials(headers) == ([("cookie", "a=1"), ("cookie", "b=2")], True)


def test_cookie_with_a_similar_name_is_kept():
    headers = [("cookie", "xharp_session=1; harp_session_2=2")]
    assert strip_harp_credentials(headers) == (headers, False)


def test_empty_session_cookie_is_removed():
    assert strip_harp_credentials([("cookie", "a=1; harp_session=")]) == ([("cookie", "a=1")], True)


def test_quoted_session_cookie_is_removed():
    assert strip_harp_credentials([("cookie", 'harp_session="abc"; a=1')]) == ([("cookie", "a=1")], True)

import time

import pytest

from harp_apps.rules.models.patterns import Pattern


@pytest.mark.parametrize(
    ("source", "value", "expected"),
    [
        ("foo", "foo", True),
        ("foo", "foobar", False),
        ("foo", "xfoo", False),
        ("", "", True),
        ("", "a", False),
        ("*", "", True),
        ("*", "anything/at/all", True),
        ("foo*", "foo", True),
        ("foo*", "foobar", True),
        ("foo*", "xfoo", False),
        ("*foo", "xfoo", True),
        ("*foo", "foox", False),
        ("*foo*", "xfoox", True),
        ("*foo*", "fo", False),
        ("a*b", "ab", True),
        ("a*b", "a/x/b", True),
        ("a*b", "a/x/c", False),
        ("a*a", "a", False),
        ("a*a", "aa", True),
        ("a**b", "ab", True),
        ("GET /api/*/items", "GET /api/1/items", True),
        ("GET /api/*/items", "GET /api/1/2/items", True),
        ("GET /api/*/items", "GET /api/1/item", False),
        ("a*b*c", "abc", True),
        ("a*b*c", "acb", False),
        ("a*b*b", "abb", True),
        ("a*b*b", "ab", False),
        ("*ab*ab", "abab", True),
        ("*ab*ab", "aab", False),
        ("a.c", "abc", False),
        ("a.c", "a.c", True),
    ],
)
def test_match(source, value, expected):
    assert bool(Pattern(source).match(value)) is expected


@pytest.mark.parametrize("matching", [False, True])
def test_match_many_wildcards_is_linear(matching):
    pattern = Pattern("*a" * 12 + ("*" if matching else "*b"))
    value = "a" * 5000

    start = time.perf_counter()
    result = pattern.match(value)
    elapsed = time.perf_counter() - start

    assert bool(result) is matching
    assert elapsed < 0.5

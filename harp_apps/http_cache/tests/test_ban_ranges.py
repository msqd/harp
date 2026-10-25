"""The keys a ban covers, as ranges of keys: what reclamation deletes, and what lookups test one key against."""

import pytest

from harp_apps.http_cache.records import BanKind, ban_prefixes, covered_ranges

KEYS = [
    "http://api/",
    "http://api/users",
    "http://api/users?abc",
    "http://api/users/",
    "http://api/users/42",
    "http://api/users/42?abc",
    "http://api/users/42/posts/1",
    "http://api/usersx",
    "http://api/usersx/1",
    "http://api/users-2",
    "http://api/users0",
    "http://api/users@",
    "http://api/user",
    "http://api/a/b/c?x/y",
    "http://api2/users",
    "http://api:8080/users",
    "https://api/users",
    "https://api/users/42",
]

PREFIXES = [
    "",
    "http://api/",
    "https://api/",
    "http://api/users",
    "http://api/users/",
    "http://api/users/42",
    "http://api/a",
    "http://api/a/b/",
]


def in_ranges(key, ranges):
    return any(low <= key and (high is None or key < high) for low, high in ranges)


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("key", KEYS)
def test_a_prefix_ban_covers_the_keys_in_its_ranges_and_no_others(prefix, key):
    assert in_ranges(key, covered_ranges(BanKind.PREFIX, prefix)) == (prefix in ban_prefixes(key))


@pytest.mark.parametrize("key", KEYS)
def test_an_exact_ban_covers_its_key_only(key):
    ranges = covered_ranges(BanKind.EXACT, key)

    assert [other for other in KEYS if in_ranges(other, ranges)] == [key]


def test_the_empty_prefix_is_one_open_range():
    assert covered_ranges(BanKind.PREFIX, "") == [("", None)]

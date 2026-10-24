"""Cache entries keep the same on-disk YAML format whichever (pure or libyaml) implementation reads/writes them."""

import pytest
import yaml

from harp_apps.http_cache.adapters import _dump_entry, _load_entry

_ENTRY = {
    "id": "6f1f4c0e-7a3b-5c52-9a43-0d2f3f1b9a10",
    "request": {
        "method": "GET",
        "url": "https://example.com/a?b=c&d=é",
        "headers": "Accept: */*\nX-Binary: \\x00\\xff\n",
        "varying": {"accept-encoding": "gzip"},
        "extensions": {"timeout": {"connect": 5.0}},
    },
    "response": {
        "status": 200,
        "headers": "Content-Type: application/json\nSet-Cookie: a=b; Expires=Wed, 21 Oct 2026 07:28:00 GMT\n",
        "varying": {},
        "body": '{"é": "\\u00e9", "multi": "line\\nbreak"}\x01\n',
        "extensions": {"http_version": "HTTP/1.1", "reason_phrase": "OK"},
    },
    "metadata": {
        "cache_key": "abc123",
        "created_at": "Tue, 14 Nov 2023 22:13:20 GMT",
        "created_at_ts": 1_700_000_000.5,
        "deleted_at": None,
        "number_of_uses": 3,
    },
    "extra": {"number_of_uses": 3},
}


def _old_dump(data) -> bytes:
    return yaml.safe_dump(data, sort_keys=False).encode()


def _old_load(raw: bytes):
    return yaml.safe_load(raw.decode())


def test_entry_dumped_by_pure_dumper_loads_with_new_loader():
    assert _load_entry(_old_dump(_ENTRY)) == _ENTRY


def test_entry_dumped_by_new_dumper_loads_with_pure_loader():
    assert _old_load(_dump_entry(_ENTRY)) == _ENTRY


def test_new_dumper_roundtrips():
    assert _load_entry(_dump_entry(_ENTRY)) == _ENTRY


@pytest.mark.skipif(not yaml.__with_libyaml__, reason="libyaml not available")
def test_uses_libyaml_when_available():
    from harp_apps.http_cache import adapters

    assert adapters._Dumper is yaml.CSafeDumper
    assert adapters._Loader is yaml.CSafeLoader


def test_long_escaped_body_roundtrips_both_ways():
    # libyaml folds long double-quoted (escaped) scalars differently than the pure emitter: bytes differ, content must not.
    entry = {"response": {"body": "é\x01 " * 80}}
    assert _load_entry(_old_dump(entry)) == entry
    assert _old_load(_dump_entry(entry)) == entry


def test_dump_preserves_key_order():
    assert _dump_entry(_ENTRY).decode().splitlines()[0].startswith("id:")
    assert _dump_entry({"b": 1, "a": 2}) == b"b: 1\na: 2\n"

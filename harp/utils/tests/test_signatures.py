import inspect

import pytest

from harp.utils import signatures
from harp.utils.signatures import resolve_arguments


def test_resolve_arguments_uses_candidates_and_defaults():
    def subject(a, b=2, c=3): ...

    assert resolve_arguments(subject, a=1, c=9) == [1, 2, 9]


def test_resolve_arguments_skips_keyword_only():
    def subject(a, *, b): ...

    assert resolve_arguments(subject, a=1) == [1]


def test_resolve_arguments_fails_on_missing_required():
    def subject(a, b): ...

    with pytest.raises(TypeError, match="Unable to resolve arguments"):
        resolve_arguments(subject, a=1)


def test_signature_is_memoized_per_subject(monkeypatch):
    # signature() runs on every request; controllers are stable, so it must be computed once per
    # subject and reused, not recomputed on each call.
    signatures._cached_signature.cache_clear()
    calls = {"n": 0}
    real_signature = inspect.signature

    def counting_signature(subject):
        calls["n"] += 1
        return real_signature(subject)

    monkeypatch.setattr(signatures, "signature", counting_signature)

    def subject(a, b=2): ...

    first = resolve_arguments(subject, a=1, b=5)
    second = resolve_arguments(subject, a=1, b=5)

    assert first == second == [1, 5]
    assert calls["n"] == 1

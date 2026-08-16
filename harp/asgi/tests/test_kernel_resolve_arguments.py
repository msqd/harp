import inspect

from harp.asgi import kernel
from harp.asgi.kernel import ASGIKernel


def test_resolve_arguments_uses_candidates_and_defaults():
    k = ASGIKernel()

    def subject(a, b=2, c=3): ...

    args, kwargs = k._resolve_arguments(subject, a=1, c=9)
    assert args == [1, 2, 9]
    assert kwargs == {}


def test_signature_is_memoized_per_subject(monkeypatch):
    # signature() runs on every request; controllers are stable, so it must be computed once per
    # subject and reused, not recomputed on each call.
    kernel._cached_signature.cache_clear()
    calls = {"n": 0}
    real_signature = inspect.signature

    def counting_signature(subject):
        calls["n"] += 1
        return real_signature(subject)

    monkeypatch.setattr(kernel, "signature", counting_signature)

    def subject(a, b=2): ...

    k = ASGIKernel()
    first, _ = k._resolve_arguments(subject, a=1, b=5)
    second, _ = k._resolve_arguments(subject, a=1, b=5)

    assert first == second == [1, 5]
    assert calls["n"] == 1

"""Every storage HARP uses must be callable by hishel, doubles included.

https://github.com/msqd/harp/issues/908: ``MockAsyncStorage.update_entry`` took
``(entry, request, response)`` while hishel calls ``(id, new_entry)``. A double whose
signature the real code could never call cannot be exercised by the code path it exists to
cover, so every test that appeared to reach the update path raised ``TypeError`` instead of
asserting. That is how both halves of https://github.com/msqd/harp/issues/906 shipped
unnoticed.

The check below compares against :class:`hishel.AsyncBaseStorage` **as installed**, not
against a list written here. A guard that enumerates the expected parameter names would
reproduce exactly the defect it is meant to prevent, one level up: it would keep passing
after hishel changed its own signatures.
"""

import inspect

import pytest
from hishel import AsyncBaseStorage

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests.conftest import MockAsyncStorage

# Everything hishel's cache proxy calls on a storage. `close` is included because the transport
# calls it on shutdown.
CONTRACT = ["create_entry", "get_entries", "update_entry", "remove_entry", "close"]

IMPLEMENTATIONS = [AsyncStorage, MockAsyncStorage]


def _positional_names(method):
    """Parameter names hishel can pass positionally, in order, `self` excluded."""
    return [
        name
        for name, parameter in inspect.signature(method).parameters.items()
        if name != "self" and parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ]


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("name", CONTRACT)
def test_storage_signature_matches_hishel(implementation, name):
    """Each method accepts what hishel passes, under the names hishel's own base declares."""
    expected = _positional_names(getattr(AsyncBaseStorage, name))
    actual = _positional_names(getattr(implementation, name))

    assert actual == expected, (
        f"{implementation.__name__}.{name}{tuple(actual)} cannot be called by hishel, "
        f"which calls {name}{tuple(expected)}. See issue #908."
    )


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS, ids=lambda cls: cls.__name__)
def test_storage_implements_the_whole_contract(implementation):
    """Nothing hishel calls is left to the abstract base, and nothing is missing.

    Paired with the signature check above: matching signatures on a method that does not
    exist would be vacuously true.
    """
    for name in CONTRACT:
        assert getattr(implementation, name, None) is not None, f"{implementation.__name__} has no {name}"
        assert inspect.iscoroutinefunction(getattr(implementation, name)), (
            f"{implementation.__name__}.{name} is not awaitable, but hishel awaits it"
        )


def test_the_contract_list_is_the_whole_of_hishel_s_interface():
    """`CONTRACT` above is not allowed to drift behind hishel's abstract methods.

    If hishel adds an abstract method, this fails rather than the suite quietly checking a
    shorter contract than the one HARP has to satisfy.
    """
    abstract = set(AsyncBaseStorage.__abstractmethods__)
    assert abstract - set(CONTRACT) == set(), (
        f"hishel declares abstract methods this test does not check: {sorted(abstract - set(CONTRACT))}"
    )

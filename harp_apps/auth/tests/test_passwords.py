import asyncio

import pytest
from argon2 import PasswordHasher as Argon2

from harp_apps.auth.passwords import PasswordHasher, PasswordPolicyError, check_policy

GOOD = "correct horse battery staple"


def test_policy_accepts_a_long_passphrase_without_any_composition_rule():
    check_policy("a" * 14 + "b")  # 15 characters, one letter case, no digit, no symbol


@pytest.mark.parametrize("password", ["", "a" * 14, "é" * 14])
def test_policy_refuses_fewer_than_15_characters(password):
    with pytest.raises(PasswordPolicyError, match="15"):
        check_policy(password)


def test_policy_counts_characters_not_bytes():
    check_policy("é" * 15)  # 30 bytes, 15 characters


def test_policy_refuses_more_than_256_characters():
    check_policy("a" * 256)
    with pytest.raises(PasswordPolicyError, match="256"):
        check_policy("a" * 257)


def test_policy_refuses_a_common_password_whatever_its_case():
    # the only entry of the bundled list that is long enough
    with pytest.raises(PasswordPolicyError, match="common"):
        check_policy("films+pic+galeries")
    with pytest.raises(PasswordPolicyError, match="common"):
        check_policy("Films+Pic+Galeries")


async def test_hash_is_an_argon2id_phc_string_with_the_owasp_parameters():
    stored = await PasswordHasher().hash(GOOD)

    assert stored.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


async def test_hash_is_salted():
    hasher = PasswordHasher()

    assert await hasher.hash(GOOD) != await hasher.hash(GOOD)


async def test_verify_accepts_the_password_and_refuses_another():
    hasher = PasswordHasher()
    stored = await hasher.hash(GOOD)

    assert await hasher.verify(GOOD, stored) is True
    assert await hasher.verify(GOOD + "!", stored) is False


async def test_verify_treats_equivalent_unicode_forms_as_the_same_password():
    hasher = PasswordHasher()
    stored = await hasher.hash("é" * 15)  # decomposed é

    assert await hasher.verify("é" * 15, stored) is True


async def test_verify_refuses_what_is_not_a_hash_instead_of_raising():
    assert await PasswordHasher().verify(GOOD, "not a hash") is False
    assert await PasswordHasher().verify(GOOD, "") is False


async def test_a_hash_with_other_parameters_needs_a_rehash():
    weaker = Argon2(time_cost=1, memory_cost=8, parallelism=1).hash(GOOD)
    hasher = PasswordHasher()

    assert hasher.needs_rehash(weaker) is True
    assert hasher.needs_rehash(await hasher.hash(GOOD)) is False


async def test_an_unknown_account_pays_a_verification(monkeypatch):
    hasher = PasswordHasher()
    calls = []
    original = hasher._verify_sync

    def spy(password, stored):
        calls.append(stored)
        return original(password, stored)

    monkeypatch.setattr(hasher, "_verify_sync", spy)

    await hasher.verify_unknown(GOOD)

    assert len(calls) == 1 and calls[0].startswith("$argon2id$")


async def test_concurrent_verifications_are_capped(monkeypatch):
    hasher = PasswordHasher(max_concurrent=2)
    stored = await hasher.hash(GOOD)
    running, peak = 0, 0
    original = hasher._verify_sync

    def slow(password, stored):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        try:
            import time

            time.sleep(0.05)
            return original(password, stored)
        finally:
            running -= 1

    monkeypatch.setattr(hasher, "_verify_sync", slow)

    await asyncio.gather(*(hasher.verify(GOOD, stored) for _ in range(6)))

    assert peak == 2


async def test_when_the_queue_is_full_a_verification_is_refused_at_once(monkeypatch):
    from harp_apps.auth.passwords import HasherBusy

    hasher = PasswordHasher(max_concurrent=1, max_waiting=2)
    stored = await hasher.hash(GOOD)
    original = hasher._verify_sync

    def slow(password, stored):
        import time

        time.sleep(0.2)
        return original(password, stored)

    monkeypatch.setattr(hasher, "_verify_sync", slow)

    results = await asyncio.gather(*(hasher.verify(GOOD, stored) for _ in range(8)), return_exceptions=True)

    assert sum(isinstance(r, HasherBusy) for r in results) == 5  # one running, two waiting
    assert [r for r in results if not isinstance(r, Exception)] == [True] * 3


async def test_the_queue_empties_after_a_refusal(monkeypatch):
    from harp_apps.auth.passwords import HasherBusy

    hasher = PasswordHasher(max_concurrent=1, max_waiting=0)
    stored = await hasher.hash(GOOD)
    results = await asyncio.gather(*(hasher.verify(GOOD, stored) for _ in range(3)), return_exceptions=True)
    assert any(isinstance(r, HasherBusy) for r in results)

    assert await hasher.verify(GOOD, stored) is True

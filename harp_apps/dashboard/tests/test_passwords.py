import sys

import pytest
import structlog
from pydantic import ValidationError

from harp_apps.dashboard.passwords import ALGORITHMS, PBKDF2_ROUNDS, hash_password, verify_password
from harp_apps.dashboard.settings.auth import BasicAuthSettings

# Made by passlib 1.7.4 (`pbkdf2_sha256.hash`): users keep hashes made before passlib was removed.
PASSLIB_HASH = "$pbkdf2-sha256$29000$lBIiBGBsTSlFSOm9lzJG6A$mRcw4nG0WXOlA8LQukkQDXW7BOWvLfrQTXtktXiD4.Y"
PASSLIB_HASH_NON_ASCII = "$pbkdf2-sha256$1000$TAkhZGxNyfnfu9daC.Ecww$g0EQpCW/jm6ws6GOuXtkGtKbvxioSzDxtlgBQarItrw"


def test_passlib_hash_is_verified_without_rehash():
    assert verify_password("pbkdf2_sha256", "s3cretAlice", PASSLIB_HASH) is True
    assert verify_password("pbkdf2_sha256", "wrong", PASSLIB_HASH) is False


def test_passlib_hash_of_non_ascii_password_is_verified():
    assert verify_password("pbkdf2_sha256", "päss", PASSLIB_HASH_NON_ASCII) is True


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_every_accepted_algorithm_hashes_and_verifies(algorithm):
    if algorithm == "argon2":
        pytest.importorskip("argon2")
    stored = hash_password(algorithm, "s3cretAlice")

    assert verify_password(algorithm, "s3cretAlice", stored) is True
    assert verify_password(algorithm, "wrong", stored) is False


def test_pbkdf2_hash_is_in_passlib_format():
    assert hash_password("pbkdf2_sha256", "x").startswith("$pbkdf2-sha256$")


@pytest.mark.parametrize("stored", ["", "garbage", "$pbkdf2-sha256$x$y$z", "$pbkdf2-sha256$29000$!!!$!!!"])
def test_malformed_pbkdf2_hash_raises_value_error(stored):
    with pytest.raises(ValueError):
        verify_password("pbkdf2_sha256", "x", stored)


def test_malformed_argon2_hash_raises_value_error():
    pytest.importorskip("argon2")
    with pytest.raises(ValueError):
        verify_password("argon2", "x", "garbage")


@pytest.mark.parametrize("algorithm", ["bcrypt", "md5_crypt", "lmhash", "hex_digest", "sha512_crypt"])
def test_other_algorithms_are_refused_at_validation_with_the_allowed_ones(algorithm):
    with pytest.raises(ValidationError) as exc:
        BasicAuthSettings(algorithm=algorithm)

    message = str(exc.value)
    assert algorithm in message
    assert "pbkdf2_sha256" in message and "argon2" in message


def test_plain_is_still_an_alias_of_plaintext():
    assert BasicAuthSettings(algorithm="plain").algorithm == "plaintext"


def test_plaintext_warns_at_validation():
    with structlog.testing.capture_logs() as logs:
        BasicAuthSettings(algorithm="plaintext", users={"a": "b"})

    assert any(log["log_level"] == "warning" and "plaintext" in log["event"] for log in logs)


def test_pbkdf2_does_not_warn():
    with structlog.testing.capture_logs() as logs:
        BasicAuthSettings(algorithm="pbkdf2_sha256")

    assert not logs


def test_argon2_without_its_extra_fails_with_the_extra_to_install(monkeypatch):
    monkeypatch.setitem(sys.modules, "argon2", None)

    with pytest.raises(ValidationError, match=r"harp-proxy\[argon2\]"):
        BasicAuthSettings(algorithm="argon2")


def test_basic_auth_checks_a_passlib_hash():
    settings = BasicAuthSettings(algorithm="pbkdf2_sha256", users={"alice": PASSLIB_HASH})

    assert settings.check("alice", "s3cretAlice") == "alice"
    assert settings.check("alice", "wrong") is False


def _rounds(stored):
    return int(stored.split("$")[2])


def test_dummy_hash_costs_as_much_as_a_configured_passlib_hash():
    settings = BasicAuthSettings(algorithm="pbkdf2_sha256", users={"alice": PASSLIB_HASH})

    assert settings._dummy_hash.startswith("$pbkdf2-sha256$")
    assert _rounds(settings._dummy_hash) == 29000


def test_dummy_hash_uses_the_costliest_configured_hash():
    settings = BasicAuthSettings(
        algorithm="pbkdf2_sha256", users={"a": PASSLIB_HASH_NON_ASCII, "b": PASSLIB_HASH, "c": "garbage"}
    )

    assert _rounds(settings._dummy_hash) == 29000


def test_dummy_hash_defaults_without_users():
    assert _rounds(BasicAuthSettings(algorithm="pbkdf2_sha256")._dummy_hash) == PBKDF2_ROUNDS


def test_dummy_hash_argon2_has_the_configured_parameters():
    argon2 = pytest.importorskip("argon2")
    cheap = argon2.PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("x")
    settings = BasicAuthSettings(algorithm="argon2", users={"a": cheap})

    assert argon2.extract_parameters(settings._dummy_hash) == argon2.extract_parameters(cheap)


CHEAP = PASSLIB_HASH  # 29000 rounds, the other users have 600000


@pytest.fixture
def pbkdf2_rounds(monkeypatch):
    """Rounds of every PBKDF2 derivation done, the work a check does."""
    from harp_apps.dashboard import passwords

    done = []
    original = passwords._pbkdf2

    def spy(password, salt, rounds):
        done.append(rounds)
        return original(password, salt, rounds)

    monkeypatch.setattr(passwords, "_pbkdf2", spy)
    return done


@pytest.fixture
def mixed_costs_settings():
    costly = hash_password("pbkdf2_sha256", "s3cretBob")
    settings = BasicAuthSettings(algorithm="pbkdf2_sha256", users={"alice": CHEAP, "bob": costly, "eve": "garbage"})
    settings._dummy_hash  # computed at configuration, not counted in the work of a check
    return settings


@pytest.mark.parametrize(
    "username, password",
    [
        ("nobody", "x"),
        ("alice", "wrong"),
        ("alice", "s3cretAlice"),
        ("bob", "wrong"),
        ("bob", "s3cretBob"),
        ("eve", "x"),
    ],
)
def test_every_check_costs_the_costliest_configured_hash(mixed_costs_settings, pbkdf2_rounds, username, password):
    mixed_costs_settings.check(username, password)

    assert sum(pbkdf2_rounds) == PBKDF2_ROUNDS


def test_mixed_costs_warn_at_validation():
    with structlog.testing.capture_logs() as logs:
        BasicAuthSettings(algorithm="pbkdf2_sha256", users={"a": CHEAP, "b": hash_password("pbkdf2_sha256", "x")})

    assert any(log["log_level"] == "warning" and "rehash" in log["event"] for log in logs)


def test_same_costs_do_not_warn():
    with structlog.testing.capture_logs() as logs:
        BasicAuthSettings(algorithm="pbkdf2_sha256", users={"a": CHEAP, "b": CHEAP})

    assert not logs


async def test_verifications_run_on_a_dedicated_bounded_executor(monkeypatch):
    import asyncio
    import threading
    import time

    from harp_apps.dashboard.settings import auth

    settings = BasicAuthSettings(algorithm="plaintext", users={"a": "b"})
    running, peak, threads = 0, 0, set()
    lock = threading.Lock()

    def slow_check(self, username, password):
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
            threads.add(threading.current_thread().name)
        time.sleep(0.05)
        with lock:
            running -= 1
        return False

    monkeypatch.setattr(BasicAuthSettings, "check", slow_check)

    await asyncio.gather(*(settings.acheck("a", f"p{i}") for i in range(4 * auth.VERIFY_WORKERS)))

    assert 1 < peak <= auth.VERIFY_WORKERS
    assert all(name.startswith(auth.VERIFY_THREAD_PREFIX) for name in threads)

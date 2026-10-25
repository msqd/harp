"""Dashboard user passwords never leave in ``secure`` dumps, whatever the algorithm."""

import pytest

from harp.config.asdict import asdict
from harp_apps.dashboard.passwords import hash_password
from harp_apps.dashboard.settings import DashboardSettings

# Random salt: parametrize ids must be explicit, or they differ per xdist worker.
HASHED = hash_password("pbkdf2_sha256", "s3cretAlice")


def _settings(algorithm, password):
    return DashboardSettings(auth={"type": "basic", "algorithm": algorithm, "users": {"alice": password}})


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize(
    "algorithm, password",
    [("plain", "s3cretAlice"), ("plaintext", "s3cretAlice"), ("pbkdf2_sha256", HASHED)],
    ids=["plain", "plaintext", "pbkdf2_sha256"],
)
def test_user_passwords_are_masked(algorithm, password, mode):
    dumped = asdict(_settings(algorithm, password), verbose=True, mode=mode)

    assert dumped["auth"]["users"]["alice"] == {"password": "***"}


def test_unsecure_shows_user_passwords():
    dumped = asdict(_settings("plain", "s3cretAlice"), secure=False)

    assert dumped["auth"]["users"]["alice"] == {"password": "s3cretAlice"}


@pytest.mark.parametrize(
    "algorithm, password",
    [("plain", "s3cretAlice"), ("pbkdf2_sha256", HASHED)],
    ids=["plain", "pbkdf2_sha256"],
)
def test_basic_auth_still_checks_the_real_password(algorithm, password):
    settings = _settings(algorithm, password)
    asdict(settings, verbose=True)

    assert settings.auth.check("alice", "s3cretAlice") == "alice"
    assert settings.auth.check("alice", "wrong") is False

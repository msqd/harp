"""Password hashing and verification for the dashboard users.

``pbkdf2_sha256`` reads and writes the format passlib used (``$pbkdf2-sha256$<rounds>$<salt>$<checksum>``, with its
"adapted" base64), so hashes made before passlib was removed keep working. ``argon2`` needs the ``argon2`` extra.
"""

import base64
import hashlib
import hmac
import secrets
from typing import Literal, get_args

TAlgorithm = Literal["pbkdf2_sha256", "argon2", "plaintext"]
ALGORITHMS: tuple[TAlgorithm, ...] = get_args(TAlgorithm)

PBKDF2_ROUNDS = 600_000
_PBKDF2_PREFIX = "$pbkdf2-sha256$"


def _ab64_encode(data: bytes) -> str:
    return base64.b64encode(data).rstrip(b"=").replace(b"+", b".").decode()


def _ab64_decode(value: str) -> bytes:
    padded = value.replace(".", "+") + "=" * (-len(value) % 4)
    return base64.b64decode(padded, validate=True)


def _pbkdf2(password: str, salt: bytes, rounds: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)


def _hash_pbkdf2_sha256(password: str, rounds: int = PBKDF2_ROUNDS, salt_size: int = 16) -> str:
    salt = secrets.token_bytes(salt_size)
    return f"{_PBKDF2_PREFIX}{rounds}${_ab64_encode(salt)}${_ab64_encode(_pbkdf2(password, salt, rounds))}"


def _parse_pbkdf2_sha256(stored: str) -> tuple[int, bytes, bytes]:
    if not stored.startswith(_PBKDF2_PREFIX):
        raise ValueError("not a pbkdf2_sha256 hash")
    try:
        rounds, salt, checksum = stored[len(_PBKDF2_PREFIX) :].split("$")
        rounds = int(rounds)
        salt, checksum = _ab64_decode(salt), _ab64_decode(checksum)
    except ValueError as exc:  # also raised by int(), split() unpacking and binascii.Error
        raise ValueError("not a pbkdf2_sha256 hash") from exc
    if rounds < 1 or not salt or not checksum:
        raise ValueError("not a pbkdf2_sha256 hash")
    return rounds, salt, checksum


def _verify_pbkdf2_sha256(password: str, stored: str) -> bool:
    rounds, salt, checksum = _parse_pbkdf2_sha256(stored)
    return hmac.compare_digest(_pbkdf2(password, salt, rounds), checksum)


def _dummy_pbkdf2_sha256(password: str, stored_hashes: list[str]) -> str:
    costliest = None
    for stored in stored_hashes:
        try:
            parsed = _parse_pbkdf2_sha256(stored)
        except ValueError:
            continue
        if costliest is None or parsed[0] > costliest[0]:
            costliest = parsed
    if costliest is None:
        return _hash_pbkdf2_sha256(password)
    return _hash_pbkdf2_sha256(password, rounds=costliest[0], salt_size=len(costliest[1]))


def _argon2():
    from argon2 import PasswordHasher

    return PasswordHasher()


def _hash_argon2(password: str) -> str:
    return _argon2().hash(password)


def _verify_argon2(password: str, stored: str) -> bool:
    from argon2.exceptions import InvalidHashError, VerificationError

    try:
        return _argon2().verify(stored, password)
    except InvalidHashError as exc:
        raise ValueError("not an argon2 hash") from exc
    except VerificationError:
        return False


def _dummy_argon2(password: str, stored_hashes: list[str]) -> str:
    from argon2 import PasswordHasher, extract_parameters
    from argon2.exceptions import InvalidHashError

    costliest = None
    for stored in stored_hashes:
        try:
            parameters = extract_parameters(stored)
        except InvalidHashError:
            continue
        cost = parameters.memory_cost * parameters.time_cost * parameters.parallelism
        if costliest is None or cost > costliest[0]:
            costliest = (cost, parameters)
    if costliest is None:
        return _hash_argon2(password)
    return PasswordHasher.from_parameters(costliest[1]).hash(password)


def _hash_plaintext(password: str) -> str:
    return password


def _verify_plaintext(password: str, stored: str) -> bool:
    return hmac.compare_digest(password.encode(), stored.encode())


_HASH = {"pbkdf2_sha256": _hash_pbkdf2_sha256, "argon2": _hash_argon2, "plaintext": _hash_plaintext}
_VERIFY = {"pbkdf2_sha256": _verify_pbkdf2_sha256, "argon2": _verify_argon2, "plaintext": _verify_plaintext}


_DUMMY = {
    "pbkdf2_sha256": _dummy_pbkdf2_sha256,
    "argon2": _dummy_argon2,
    "plaintext": lambda password, stored_hashes: password,
}


def dummy_hash(algorithm: TAlgorithm, stored_hashes: list[str]) -> str:
    """A hash as costly to verify as the costliest of ``stored_hashes`` (the default cost when none is valid)."""
    return _DUMMY[algorithm]("harp", stored_hashes)


def hash_password(algorithm: TAlgorithm, password: str) -> str:
    return _HASH[algorithm](password)


def verify_password(algorithm: TAlgorithm, password: str, stored: str) -> bool:
    """True if the password matches, False if not, ValueError if ``stored`` is not a hash of this algorithm."""
    return _VERIFY[algorithm](password, stored)

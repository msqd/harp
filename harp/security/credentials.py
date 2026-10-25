"""HARP's own credentials, as a contract of the core.

The proxy removes them before a request reaches an origin (ADR-0010), and the authentication application issues them.
Both rely on the definitions here, so the core needs no dependency on that application.

A token is ``harp_<prefix 8><secret 43><crc32 6>``: base62 only after ``harp_``, the last six characters being the
CRC32 of everything before them (``harp_`` included) written in base62, zero padded. The checksum rejects typos before
any lookup.

This module is the only parser of HARP tokens in ``Authorization``. The authentication application must reuse it and
accept nothing more lenient than it does: whatever the application would take as a HARP token, the proxy has to strip.
"""

import secrets
import zlib

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TOKEN_PREFIX = "harp_"
TOKEN_ID_LENGTH = 8
TOKEN_SECRET_LENGTH = 43
TOKEN_CHECKSUM_LENGTH = 6
TOKEN_LENGTH = len(TOKEN_PREFIX) + TOKEN_ID_LENGTH + TOKEN_SECRET_LENGTH + TOKEN_CHECKSUM_LENGTH

SESSION_COOKIE_NAME = "harp_session"
"""Dashboard session cookie over plain HTTP."""

SECURE_SESSION_COOKIE_NAME = "__Host-harp_session"
"""Dashboard session cookie over HTTPS (``__Host-`` prefixed, HttpOnly, SameSite=Lax)."""

SESSION_COOKIE_NAMES = (SECURE_SESSION_COOKIE_NAME, SESSION_COOKIE_NAME)

_BASE62_SET = frozenset(BASE62)


def _base62_checksum(body: str) -> str:
    number = zlib.crc32(body.encode())
    digits = []
    while number:
        number, remainder = divmod(number, 62)
        digits.append(BASE62[remainder])
    return "".join(reversed(digits)).rjust(TOKEN_CHECKSUM_LENGTH, BASE62[0])


def build_token(prefix: str, secret: str) -> str:
    """Assemble a token from its 8 characters prefix and its 43 characters secret (base62)."""
    body = TOKEN_PREFIX + prefix + secret
    return body + _base62_checksum(body)


def generate_token() -> str:
    """A new random token."""
    return build_token(_random_base62(TOKEN_ID_LENGTH), _random_base62(TOKEN_SECRET_LENGTH))


def _random_base62(length: int) -> str:
    return "".join(secrets.choice(BASE62) for _ in range(length))


def is_harp_token(value: str) -> bool:
    """Whether a value has the shape of a HARP token and a valid checksum. It says nothing about the token being
    issued."""
    if len(value) != TOKEN_LENGTH or not value.startswith(TOKEN_PREFIX):
        return False
    body, checksum = value[:-TOKEN_CHECKSUM_LENGTH], value[-TOKEN_CHECKSUM_LENGTH:]
    if not _BASE62_SET.issuperset(body[len(TOKEN_PREFIX) :]) or not _BASE62_SET.issuperset(checksum):
        return False
    return secrets.compare_digest(checksum, _base62_checksum(body))


def strip_harp_credentials(headers):
    """Remove HARP's own credentials from request headers, given as ``(name, value)`` pairs.

    The session cookies are removed from ``Cookie`` (the other cookies stay, and the header goes when nothing is left),
    and an ``Authorization: Bearer`` whose value is a HARP token goes too. Nothing else is touched.

    :return: the remaining pairs, and whether anything was removed.
    """
    kept, stripped = [], False
    for name, value in headers:
        lowered = name.lower()
        if lowered == "cookie":
            pieces = value.split(";")
            cookies = [c for c in pieces if c.split("=", 1)[0].strip() not in SESSION_COOKIE_NAMES]
            if len(cookies) != len(pieces):
                stripped = True
                if cookies := [c.strip() for c in cookies if c.strip()]:
                    kept.append((name, "; ".join(cookies)))
                continue
        elif lowered == "authorization":
            scheme, _, token = value.strip().partition(" ")
            if scheme.lower() == "bearer" and is_harp_token(token.strip()):
                stripped = True
                continue
        kept.append((name, value))
    return kept, stripped


def strip_harp_set_cookies(headers):
    """Remove from response headers, given as ``(name, value)`` pairs, every ``Set-Cookie`` naming a HARP session
    cookie: an origin must not plant or overwrite the dashboard session, which browsers share across ports.

    :return: the remaining pairs, and whether anything was removed.
    """
    kept = [
        (name, value)
        for name, value in headers
        if name.lower() != "set-cookie" or value.split("=", 1)[0].strip() not in SESSION_COOKIE_NAMES
    ]
    return kept, len(kept) != len(headers)

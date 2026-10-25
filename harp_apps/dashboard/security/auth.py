import secrets
from typing import Optional

from passlib.hash import pbkdf2_sha256

from harp import get_logger
from harp.security.actor import Actor, ActorAccount, Role
from harp_apps.dashboard.settings.auth import BasicAuthSettings, NoAuthSettings, User

logger = get_logger(__name__)

GENERATED_USERNAME = "admin"

#: Who acts when the dashboard is explicitly left open (``auth: {type: none}``): nobody signed in, so no account, and
#: everything allowed as before. It authors favourites as the system account does.
OPEN_ACTOR = Actor(account=ActorAccount(id=None, username="anonymous", role=Role.ADMIN), role=Role.ADMIN, via="open")


def resolve_authentication(
    auth: Optional[BasicAuthSettings | NoAuthSettings], bind: str
) -> Optional[BasicAuthSettings]:
    """
    Returns the basic authentication enforced by the dashboard, or None if it was explicitly left open.

    Without configured authentication, a random password is generated and logged once. It is only kept as a hash.
    The warning names the address the dashboard listens on (``bind``).
    """
    if isinstance(auth, NoAuthSettings):
        return None

    if auth is not None:
        return auth

    password = secrets.token_urlsafe(24)
    logger.warning(
        f"Dashboard login on {bind} (generated for this boot only): username={GENERATED_USERNAME} password={password} "
        "— set dashboard.auth to choose your own."
    )
    return BasicAuthSettings(
        type="basic",
        algorithm="pbkdf2_sha256",
        users={GENERATED_USERNAME: User(password=pbkdf2_sha256.hash(password))},
    )

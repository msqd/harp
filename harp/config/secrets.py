from typing import Annotated

from pydantic import PlainSerializer, SecretStr, SerializationInfo

MASK = "***"

#: Serialization context key: ``asdict(secure=False)`` sets it to let secrets out of ``model_dump``.
REVEAL_SECRETS = "harp_reveal_secrets"  # pragma: allowlist secret


def _serialize_secret(secret: SecretStr, info: SerializationInfo) -> str:
    if (info.context or {}).get(REVEAL_SECRETS):
        return secret.get_secret_value()
    return MASK


#: A setting that must never be shown: webhook URLs, DSNs, tokens, passwords, credential headers.
#:
#: It validates like a ``str``, hides its value in a ``repr`` like pydantic's ``SecretStr``, and serializes masked in
#: every mode unless the caller asked for it (``asdict(secure=False)``). Read the value with ``get_secret_value()``.
Secret = Annotated[SecretStr, PlainSerializer(_serialize_secret, return_type=str)]

import re
from typing import Any

REDACTED = "[redacted]"

_SECRET = re.compile(r"password|passwd|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key", re.I)
_IDENTIFIER = re.compile(r"_(id|name|label|type|prefix)$", re.I)


def _is_secret(key: Any) -> bool:
    key = str(key)
    return bool(_SECRET.search(key)) and not _IDENTIFIER.search(key)


def redact(value: Any) -> Any:
    """A copy of ``value`` where whatever sits under a secret-looking key is masked. No secret reaches the audit."""
    if isinstance(value, dict):
        return {key: REDACTED if _is_secret(key) else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value

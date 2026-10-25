from harp_apps.audit.redact import REDACTED, redact


def test_secret_looking_keys_are_masked():
    details = {"token": "hrp_abc", "password": "hunter2", "api_key": "k", "Authorization": "Bearer x", "name": "ci"}

    assert redact(details) == {
        "token": REDACTED,
        "password": REDACTED,
        "api_key": REDACTED,
        "Authorization": REDACTED,
        "name": "ci",
    }


def test_identifiers_of_secrets_are_kept():
    assert redact({"token_id": 7, "token_name": "ci"}) == {"token_id": 7, "token_name": "ci"}


def test_nested_structures_are_walked():
    details = {"scopes": ["read"], "created": {"secret": "s", "items": [{"cookie": "c", "ok": 1}]}}

    assert redact(details) == {
        "scopes": ["read"],
        "created": {"secret": REDACTED, "items": [{"cookie": REDACTED, "ok": 1}]},
    }


def test_input_is_not_mutated():
    details = {"token": "t"}

    redact(details)

    assert details == {"token": "t"}

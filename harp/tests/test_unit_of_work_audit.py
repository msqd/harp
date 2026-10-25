import pytest

from harp.unit_of_work.audit import AuditableEvent, is_secret_field


@pytest.mark.parametrize("name", ["password", "pwd", "secret", "token", "api_key", "key", "auth", "recovery_codes"])
def test_an_event_cannot_declare_a_field_named_like_a_secret(name):
    with pytest.raises(TypeError, match=name):

        class Leaky(AuditableEvent):
            details_fields = ("name", name)


@pytest.mark.parametrize("name", ["prefix", "name", "token_id", "token_name", "from", "to", "role"])
def test_ordinary_fields_may_be_declared(name):
    assert not is_secret_field(name)

    class Fine(AuditableEvent):
        details_fields = (name,)

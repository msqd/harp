import pytest

from harp.http import HttpRequest
from harp.security.actor import Actor as SecurityActor
from harp.security.actor import ActorAccount, Role, set_actor
from harp.unit_of_work.audit import Actor, AuditableEvent, audit_actor, is_secret_field


def _request(**kwargs):
    return HttpRequest(headers={"user-agent": "Firefox/141"})


def test_the_audit_actor_is_the_account_with_its_credential_and_where_it_comes_from():
    request = _request()
    set_actor(
        request,
        SecurityActor(
            account=ActorAccount(id=7, username="ed", role=Role.EDITOR),
            role=Role.EDITOR,
            via="token",
            via_id="tok_8f3a",
            client="agent",
        ),
    )

    actor = audit_actor(request)

    assert (actor.account_id, actor.label, actor.via, actor.via_id, actor.client) == (
        7,
        "ed",
        "token",
        "tok_8f3a",
        "agent",
    )
    assert actor.user_agent == "Firefox/141"


def test_a_numeric_credential_id_stays_a_string():
    request = _request()
    set_actor(
        request,
        SecurityActor(
            account=ActorAccount(id=7, username="ed", role=Role.EDITOR), role=Role.EDITOR, via="session", via_id="211"
        ),
    )

    assert audit_actor(request).via_id == "211"


def test_a_request_without_actor_is_a_system_actor_that_still_says_where_it_comes_from():
    actor = audit_actor(_request())

    assert actor == Actor(user_agent="Firefox/141", ip=actor.ip)


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

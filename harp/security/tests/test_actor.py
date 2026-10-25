import pytest

from harp.http import HttpRequest
from harp.security.actor import Actor, ActorAccount, Role, effective_role, get_actor, set_actor


def make_actor(role=Role.EDITOR, **kwargs):
    return Actor(account=ActorAccount(id=1, username="alice", role=role), role=role, via="basic", **kwargs)


def test_roles_are_ordered():
    assert Role.VIEWER < Role.EDITOR < Role.ADMIN


def test_roles_are_named_after_their_label():
    assert [role.label for role in Role] == ["viewer", "editor", "admin"]
    assert Role.parse("editor") is Role.EDITOR


def test_unknown_role_is_refused():
    with pytest.raises(ValueError, match="root"):
        Role.parse("root")


@pytest.mark.parametrize(
    "account, cap, expected",
    [
        (Role.ADMIN, None, Role.ADMIN),
        (Role.ADMIN, Role.VIEWER, Role.VIEWER),
        (Role.VIEWER, Role.ADMIN, Role.VIEWER),
        (Role.EDITOR, Role.EDITOR, Role.EDITOR),
    ],
)
def test_effective_role_is_the_lowest_of_account_role_and_credential_cap(account, cap, expected):
    assert effective_role(account, cap) is expected


def test_actor_can_do_what_its_effective_role_includes():
    assert make_actor(Role.EDITOR).can(Role.VIEWER)
    assert make_actor(Role.EDITOR).can(Role.EDITOR)
    assert not make_actor(Role.EDITOR).can(Role.ADMIN)


def test_actor_context_carries_the_credential_and_the_client():
    actor = make_actor(via_id="42", client="agent")

    assert (actor.account.username, actor.via, actor.via_id, actor.client) == ("alice", "basic", "42", "agent")


def test_actor_travels_with_the_request():
    request = HttpRequest()
    assert get_actor(request) is None

    actor = make_actor()
    set_actor(request, actor)

    assert get_actor(request) is actor

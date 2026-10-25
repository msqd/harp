from unittest.mock import MagicMock

from harp.http import HttpRequest
from harp.security.actor import Actor, ActorAccount, Role, set_actor
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.security.auth import OPEN_ACTOR


def controller():
    return SystemController(storage=MagicMock(), settings=MagicMock(), resolver=MagicMock())


async def test_system_tells_who_is_acting_and_with_which_role():
    request = HttpRequest()
    account = ActorAccount(id=3, username="alice", role=Role.ADMIN, display_name="Alice A.")
    # a token capped to Viewer: the role shown is the one the request acts with, not the account's
    set_actor(request, Actor(account=account, role=Role.VIEWER, via="token", via_id="9"))

    response = await controller().get(request)

    assert (response["user"], response["displayName"], response["role"]) == ("alice", "Alice A.", "viewer")


async def test_system_names_the_anonymous_actor_of_an_open_dashboard():
    request = HttpRequest()
    set_actor(request, OPEN_ACTOR)

    response = await controller().get(request)

    assert (response["user"], response["role"]) == ("anonymous", "admin")

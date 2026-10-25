from unittest.mock import AsyncMock, MagicMock

from multidict import MultiDict

from harp.http import HttpRequest
from harp.security.actor import Actor, ActorAccount, Role, set_actor
from harp_apps.dashboard.controllers.transactions import TransactionsController


def request_of(username, method="GET"):
    request = HttpRequest(method=method)
    request.query = MultiDict()
    set_actor(
        request, Actor(account=ActorAccount(id=3, username=username, role=Role.VIEWER), role=Role.VIEWER, via="basic")
    )
    return request


def controller():
    storage = MagicMock()
    storage.get_transaction = AsyncMock(return_value=None)
    storage.set_user_flag = AsyncMock()
    return TransactionsController(storage=storage, handle_errors=False)


async def test_favourites_belong_to_the_account_of_the_actor():
    transactions = controller()

    await transactions.set_user_flag(request_of("alice", "PUT"), "t1", "favorite")

    transactions.storage.set_user_flag.assert_awaited_once()
    assert transactions.storage.set_user_flag.await_args.kwargs["username"] == "alice"


async def test_transaction_flags_are_read_for_the_account_of_the_actor():
    transactions = controller()

    await transactions.get(request_of("alice"), "t1")

    assert transactions.storage.get_transaction.await_args.kwargs["username"] == "alice"

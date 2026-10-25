"""What the dashboard hands the audit: who acts, as the audit contract describes them."""

from harp.http import HttpRequest
from harp.security.actor import get_actor
from harp.unit_of_work.audit import Actor


def audit_actor(request: HttpRequest) -> Actor:
    """The actor of ``request`` as an audit event carries them, with where the request comes from."""
    actor = get_actor(request)
    where = {"ip": request.client_ipaddr, "user_agent": request.headers.get("user-agent")}
    if actor is None:
        return Actor(**where)
    via_id = actor.via_id
    return Actor(
        account_id=actor.account.id,
        label=actor.account.username,
        via=actor.via,
        via_id=int(via_id) if via_id is not None and str(via_id).isdigit() else None,
        client=actor.client,
        **where,
    )

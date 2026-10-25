import math
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select

from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, JsonHttpResponse
from harp.security.actor import Role, get_actor
from harp.settings import PAGE_SIZE
from harp.views.json import json
from harp_apps.audit.models import AuditEvent
from harp_apps.storage.services.sql import SqlStorage


def _like_prefix(prefix: str) -> str:
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _instant(text: str) -> datetime:
    """An ISO 8601 instant; one without a zone (``2026-10-01``) is UTC, the audit's clock."""
    value = datetime.fromisoformat(text)
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _filters(query) -> list:
    """The conditions a request asks for; each one is on a column that has an index (``actor_label`` aside)."""
    conditions = []
    if since := query.get("since"):
        conditions.append(AuditEvent.occurred_at >= _instant(since))
    if until := query.get("until"):
        conditions.append(AuditEvent.occurred_at <= _instant(until))
    if actor := query.get("actor"):
        conditions.append(AuditEvent.actor_label == actor)
    if action := query.get("action"):
        conditions.append(AuditEvent.action.like(_like_prefix(action), escape="\\"))
    if target_type := query.get("target_type"):
        conditions.append(AuditEvent.target_type == target_type)
    if target_id := query.get("target_id"):
        conditions.append(AuditEvent.target_id == target_id)
    return conditions


def _own(account_id: int | None):
    """What concerns an account: it acted, or it is the target."""
    if account_id is None:
        return AuditEvent.id.is_(None)
    return or_(
        AuditEvent.actor_account_id == account_id,
        and_(AuditEvent.target_type == "account", AuditEvent.target_id == str(account_id)),
    )


def _iso(value: datetime) -> str:
    """UTC with a ``Z``; SQLite hands timestamps back without their zone."""
    return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize(row: AuditEvent, *, own_account_id: int | None = None, hide_foreign_origin: bool = False) -> dict:
    """``hide_foreign_origin``: keep to the account how somebody else acted (the ip, user agent, credential id
    and client of an Admin who changed its role are none of its business)."""
    foreign = hide_foreign_origin and row.actor_account_id != own_account_id
    return {
        "id": row.id,
        "occurredAt": _iso(row.occurred_at),
        "action": row.action,
        "outcome": row.outcome,
        "actor": {
            "id": row.actor_account_id,
            "label": row.actor_label,
            "via": row.actor_via,
            "viaId": None if foreign else row.actor_via_id,
            "client": None if foreign else row.actor_client,
        },
        "ip": None if foreign else row.ip,
        "userAgent": None if foreign else row.user_agent,
        "target": {"type": row.target_type, "id": row.target_id, "label": row.target_label},
        "details": row.details or {},
    }


@RouterPrefix("/api/audit")
class AuditController(RoutingController):
    """Reads the audit. Nothing here writes, and no route here is reachable from an MCP tool."""

    def __init__(self, *, storage: SqlStorage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/", role=Role.ADMIN)
    async def list(self, request: HttpRequest):
        return await self._page(request, scope=[])

    @GetHandler("/mine", role=Role.VIEWER)
    async def mine(self, request: HttpRequest):
        account_id = get_actor(request).account.id
        return await self._page(request, scope=[_own(account_id)], own_account_id=account_id, hide_foreign_origin=True)

    async def _page(self, request: HttpRequest, *, scope: list, **serialization):
        try:
            conditions = [*scope, *_filters(request.query)]
            page = max(int(request.query.get("page", 1)), 1)
        except ValueError:
            return JsonHttpResponse({"error": "Invalid filter", "status": 400}, status=400)

        async with self.storage.session_factory() as session:
            total = (
                await session.execute(select(func.count()).select_from(AuditEvent).where(*conditions))
            ).scalar_one()
            rows = (
                await session.execute(
                    select(AuditEvent)
                    .where(*conditions)
                    .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
                    .limit(PAGE_SIZE)
                    .offset((page - 1) * PAGE_SIZE)
                )
            ).scalars()
            items = [_serialize(row, **serialization) for row in rows]

        return json({"items": items, "pages": math.ceil(total / PAGE_SIZE), "total": total, "perPage": PAGE_SIZE})

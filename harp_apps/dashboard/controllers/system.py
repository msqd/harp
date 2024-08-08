from typing import cast

import orjson
from sqlalchemy import func, select
from sqlalchemy.orm import aliased, joinedload

from harp import __revision__, __version__, get_logger
from harp.config import asdict
from harp.controllers import GetHandler, PutHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, HttpResponse
from harp.typing.global_settings import GlobalSettings
from harp.views.json import json
from harp_apps.proxy.settings import ProxySettings
from harp_apps.storage.models import MetricValue
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IStorage

from ..utils.dependencies import get_python_dependencies, parse_dependencies

logger = get_logger(__name__)


@RouterPrefix("/api/system")
class SystemController(RoutingController):
    def __init__(self, *, storage: IStorage, settings: GlobalSettings, handle_errors=True, router=None):
        self.settings = settings
        self.storage: SqlStorage = cast(SqlStorage, storage)

        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/")
    async def get(self, request: HttpRequest):
        context = getattr(request, "context", {})

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    @GetHandler("/proxy")
    async def get_proxy(self):
        settings: ProxySettings | None = self.settings.get("proxy", None)
        if not settings:
            return HttpResponse(b"Proxy is not configured", status=404)
        return json({"endpoints": [endpoint._asdict(with_status=True) for endpoint in settings.endpoints]})

    @PutHandler("/proxy")
    async def put_proxy(self, request: HttpRequest):
        settings: ProxySettings | None = self.settings.get("proxy", None)
        if not settings:
            return HttpResponse(b"Proxy is not configured", status=404)

        try:
            data = orjson.loads(await request.aread())
        except orjson.JSONDecodeError as exc:
            return HttpResponse(f"Invalid JSON: {exc}", status=400)

        # find endpoint
        endpoint = None
        for _endpoint in settings.endpoints:
            if _endpoint.name == data.get("endpoint"):
                endpoint = _endpoint
                break
        if not endpoint:
            return HttpResponse(f"Endpoint not found: {request.query.get('endpoint')}", status=404)

        if data.get("action") == "up":
            endpoint.remote.set_up(data.get("url"))
        elif data.get("action") == "down":
            endpoint.remote.set_down(data.get("url"))
        elif data.get("action") == "checking":
            endpoint.remote.set_checking(data.get("url"))
        else:
            return HttpResponse(b"Invalid action", status=400)

        return await self.get_proxy()

    @GetHandler("/settings")
    async def get_settings(self):
        return json(asdict(self.settings, secure=True))

    @GetHandler("/dependencies")
    async def get_dependencies(self):
        return json({"python": await self.__get_cached_python_dependencies()})

    @GetHandler("/storage")
    async def get_storage(self):
        subquery = select(
            func.rank().over(order_by=MetricValue.created_at.desc(), partition_by=MetricValue.metric_id).label("rank"),
            MetricValue,
        ).subquery()
        v = aliased(MetricValue, subquery)
        query = select(v).where(subquery.c.rank == 1).options(joinedload(v.metric))

        async with self.storage.session_factory() as session:
            result = (await session.execute(query)).scalars().all()

        return json(
            {
                "settings": asdict(self.settings.get("storage", {}), secure=True),
                "counts": {value.metric.name.split(".", 1)[-1]: value.value for value in result},
            }
        )

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies

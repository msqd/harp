from typing import cast

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import aliased, joinedload

from harp import __revision__, __version__, get_logger
from harp.config.asdict import asdict
from harp.controllers import GetHandler, ProxyControllerResolver, PutHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, HttpResponse
from harp.typing.global_settings import GlobalSettings
from harp.views.json import json
from harp_apps.storage.models import MetricValue
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IStorage

from ..utils.dependencies import get_python_dependencies, parse_dependencies
from .models.system import SystemPutProxyInput

logger = get_logger(__name__)


@RouterPrefix("/api/system")
class SystemController(RoutingController):
    def __init__(
        self,
        *,
        storage: IStorage,
        settings: GlobalSettings,
        resolver: ProxyControllerResolver,
        handle_errors=True,
        router=None,
    ):
        self.settings = settings
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.resolver = resolver

        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/")
    async def get(self, request: HttpRequest):
        user = request.extensions.get("user")

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": user,
            }
        )

    @GetHandler("/proxy")
    async def get_proxy(self):
        endpoints = list(self.resolver.endpoints.values())
        return json({"endpoints": asdict(endpoints, verbose=True)})

    @PutHandler("/proxy")
    async def put_proxy(self, request: HttpRequest):
        endpoints = list(self.resolver.endpoints.values())

        try:
            input_data = SystemPutProxyInput.model_validate_json(await request.aread())
        except ValidationError as exc:
            return HttpResponse(f"Invalid input: {exc}", status=400)

        # find endpoint
        endpoint = None
        for _endpoint in endpoints:
            if _endpoint.settings.name == input_data.endpoint:
                endpoint = _endpoint
                break
        if not endpoint:
            return HttpResponse(f"Endpoint not found: {request.query.get('endpoint')}", status=404)

        try:
            endpoint.remote[input_data.url]
        except KeyError:
            return HttpResponse(f"Endpoint URL not found: {input_data.url}", status=404)

        match input_data.action:
            case "up":
                endpoint.remote.set_up(input_data.url)
            case "down":
                endpoint.remote.set_down(input_data.url)
            case "checking":
                endpoint.remote.set_checking(input_data.url)
            case _:
                return HttpResponse(b"Invalid action", status=400)

        return await self.get_proxy()

    @GetHandler("/settings")
    async def get_settings(self):
        settings_dict = asdict(self.settings, verbose=True, secure=True, mode="python")
        return json(settings_dict)

    @GetHandler("/dependencies")
    async def get_dependencies(self):
        return json({"python": await self.__get_cached_python_dependencies()})

    @GetHandler("/storage")
    async def get_storage(self):
        subquery = select(
            func.rank()
            .over(
                order_by=MetricValue.created_at.desc(),
                partition_by=MetricValue.metric_id,
            )
            .label("rank"),
            MetricValue,
        ).subquery()
        v = aliased(MetricValue, subquery)
        query = select(v).where(subquery.c.rank == 1).options(joinedload(v.metric))

        async with self.storage.session_factory() as session:
            result = (await session.execute(query)).scalars().all()

        return json(
            {
                "settings": asdict(self.settings.get("storage", {}), secure=True, mode="python"),
                "counts": {value.metric.name.split(".", 1)[-1]: value.value for value in result},
            }
        )

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies

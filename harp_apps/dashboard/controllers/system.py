import re
from copy import deepcopy
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import aliased, joinedload

from harp import __revision__, __version__, get_logger
from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest
from harp.typing import GlobalSettings, Storage
from harp.views.json import json
from harp_apps.sqlalchemy_storage.models import MetricValue
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage

from ..utils.dependencies import get_python_dependencies, parse_dependencies

logger = get_logger(__name__)


@RouterPrefix("/api/system")
class SystemController(RoutingController):
    def __init__(self, *, storage: Storage, settings: GlobalSettings, handle_errors=True, router=None):
        # a bit of scrambling for passwords etc.
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])

        self.settings = deepcopy(dict(settings))
        self.storage: SqlAlchemyStorage = cast(SqlAlchemyStorage, storage)

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

    @GetHandler("/settings")
    async def get_settings(self):
        return json(self.settings)

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
                "settings": self.settings.get("storage", {}),
                "counts": {value.metric.name.split(".", 1)[-1]: value.value for value in result},
            }
        )

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies

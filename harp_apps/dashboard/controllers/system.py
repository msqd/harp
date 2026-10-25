from typing import cast

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import aliased, joinedload

from harp import __revision__, __version__, get_logger
from harp.config.asdict import asdict
from harp.config.development_only import development_only_settings
from harp.controllers import GetHandler, ProxyControllerResolver, PutHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, HttpResponse, JsonHttpResponse
from harp.meta import get_meta
from harp.security.actor import Role, get_actor
from harp.typedefs.global_settings import GlobalSettings
from harp.unit_of_work import IUnitOfWorkFactory
from harp.unit_of_work.audit import Target, audit_actor
from harp.views.json import json
from harp_apps.proxy.adapters import strip_credentials
from harp_apps.proxy.constants import CHECKING, DOWN, UP
from harp_apps.proxy.events import RemoteStateChangedByHand, state_name
from harp_apps.proxy.settings.remote import Remote
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
        unit_of_work: IUnitOfWorkFactory,
        handle_errors=True,
        router=None,
    ):
        self.settings = settings
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.resolver = resolver
        self.unit_of_work = unit_of_work

        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/", role=Role.VIEWER)
    async def get(self, request: HttpRequest):
        actor = get_actor(request)

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": actor.account.username,
                "displayName": actor.account.display_name,
                "role": actor.role.label,
                "development_only_settings": development_only_settings(self.settings),
            }
        )

    @GetHandler("/proxy", role=Role.EDITOR)
    async def get_proxy(self):
        endpoints = list(self.resolver.endpoints.values())
        return json({"endpoints": asdict(endpoints, verbose=True)})

    @PutHandler("/proxy", role=Role.EDITOR)
    async def put_proxy(self, request: HttpRequest):
        try:
            input_data = SystemPutProxyInput.model_validate_json(await request.aread())
        except ValidationError as exc:
            return HttpResponse(f"Invalid input: {exc}", status=400)

        endpoint = self._find_endpoint(input_data.endpoint)
        if not endpoint:
            return HttpResponse(f"Endpoint not found: {input_data.endpoint}", status=404)

        url = self._find_remote_url(endpoint, input_data.index)
        if url is None:
            return HttpResponse(f"Remote endpoint not found: {input_data.index}", status=404)

        remote: Remote = endpoint.remote
        previous = remote[url].status
        setters = {"up": remote.set_up, "down": remote.set_down, "checking": remote.set_checking}
        restorers = {UP: remote.set_up, DOWN: remote.set_down, CHECKING: remote.set_checking}

        async def change():
            setters[input_data.action](url)

        async def restore():
            restorers[previous](url)

        event = RemoteStateChangedByHand(
            actor=audit_actor(request),
            target=Target("remote", strip_credentials(url), input_data.endpoint),
            details={
                "endpoint": input_data.endpoint,
                "url": strip_credentials(url),
                "from": state_name(previous),
                "to": input_data.action,
            },
        )
        async with self.unit_of_work() as uow:
            await uow.record(event)
            await uow.act(change, compensation=restore)

        return await self.get_proxy()

    async def on_refusal(self, request: HttpRequest, handler) -> None:
        """A refused attempt to change a remote by hand is recorded as ``denied``; the refusal is sent either way."""
        actor = get_actor(request)
        if getattr(handler, "__func__", None) is not SystemController.put_proxy or actor is None:
            return
        details = {"required_role": get_meta(handler, "role").label}
        try:
            input_data = SystemPutProxyInput.model_validate_json(await request.aread())
            endpoint = self._find_endpoint(input_data.endpoint)
            url = self._find_remote_url(endpoint, input_data.index) if endpoint else None
            details |= {"endpoint": input_data.endpoint, "to": input_data.action}
            if url is not None:
                details |= {"url": strip_credentials(url), "from": state_name(endpoint.remote[url].status)}
        except ValidationError:
            pass
        try:
            async with self.unit_of_work() as uow:
                await uow.record(
                    RemoteStateChangedByHand(actor=audit_actor(request), outcome="denied", details=details)
                )
        except Exception:
            logger.exception("A refused change of a remote state could not be recorded.")

    def _find_endpoint(self, name: str):
        return next((endpoint for endpoint in self.resolver.endpoints.values() if endpoint.settings.name == name), None)

    @staticmethod
    def _find_remote_url(endpoint, index: int) -> str | None:
        """The remote is identified by position: its url is masked on the way out, so it cannot be sent back."""
        try:
            return str(endpoint.remote.endpoints[index].settings.url)
        except IndexError:
            return None

    @GetHandler("/settings", role=Role.ADMIN)
    async def get_settings(self):
        return JsonHttpResponse(
            asdict(self.settings, verbose=True, secure=True, mode="python"),
        )

    @GetHandler("/dependencies", role=Role.ADMIN)
    async def get_dependencies(self):
        return json({"python": await self.__get_cached_python_dependencies()})

    @GetHandler("/storage", role=Role.EDITOR)
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
            try:
                self._dependencies = parse_dependencies(await get_python_dependencies())
            except Exception as exc:
                logger.warning("Failed to get python dependencies", exc_info=exc)
                self._dependencies = {}
        return self._dependencies

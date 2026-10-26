from copy import deepcopy

import pytest

from harp.config import ConfigurationBuilder
from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver, ProxyControllerResolver
from harp.security.actor import Actor, ActorAccount, Role, set_actor

from harp.unit_of_work import TransactionalEventDispatcher
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.storage.unit_of_work import SqlUnitOfWorkFactory
from harp.views.json import register as register_json_views

from ..controllers.system import SystemController
from ..security.auth import OPEN_ACTOR


class SystemControllerTestFixtureMixin:
    @pytest.fixture
    async def controller(self, request, sql_storage, blob_storage):
        # retrieve settings overrides
        try:
            raw_settings = deepcopy(request.param)
        except AttributeError:
            raw_settings = {}
        raw_settings.setdefault("applications", [])
        if "storage" not in raw_settings["applications"]:
            raw_settings["applications"].append("storage")

        raw_settings.setdefault("storage", {})

        db_url = sql_storage.engine.url.render_as_string(hide_password=False)
        if raw_settings["storage"].get("url") and raw_settings["storage"]["url"] != db_url:
            raise ValueError(f"Database URL mismatch: {raw_settings['storage']['url']} != {db_url}")
        raw_settings["storage"]["url"] = db_url

        raw_settings["storage"].setdefault("blobs", {})
        raw_settings["storage"]["blobs"].setdefault("type", blob_storage.type)

        # exactly these applications: the tests here look at one controller, not at what its dependencies bring
        applications = raw_settings.pop("applications")
        builder = ConfigurationBuilder(raw_settings, use_default_applications=False)
        builder.applications.add(*applications)
        system = await builder.abuild_system(validate_dependencies=False)

        try:
            yield SystemController(
                storage=sql_storage,
                settings=system.config,
                handle_errors=False,
                resolver=system.provider.get(ProxyControllerResolver),
                # on the storage under test, with the listeners the loaded applications attached
                unit_of_work=SqlUnitOfWorkFactory.from_storage(
                    sql_storage, system.provider.get(TransactionalEventDispatcher), system.dispatcher
                ),
            )
        finally:
            await system.dispose()


def parametrize_with_settings(*args):
    return pytest.mark.parametrize("controller", args, indirect=True)


class RoleNamedActors:
    """Stands for the actor resolver: an account is named after its role, ``disabled`` is refused."""

    async def basic(self, username):
        if username == "disabled":
            return None
        role = Role.parse(username)
        return Actor(account=ActorAccount(id=1, username=username, role=role), role=role, via="basic")


class AdminThroughASGIFixtureMixin(ControllerThroughASGIFixtureMixin):
    """The controller under test is a sub-controller of the dashboard, which is what resolves the actor: here it is an
    Admin, as when the dashboard is left open."""

    @pytest.fixture
    def kernel(self, controller):
        async def as_admin(request):
            set_actor(request, OPEN_ACTOR)
            return await controller(request)

        kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=as_admin), handle_errors=False)
        register_json_views(kernel.dispatcher)
        return kernel

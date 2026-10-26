from base64 import b64encode
from copy import deepcopy

import pytest

from harp.config import ConfigurationBuilder
from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver, ProxyControllerResolver
from harp.security.actor import Actor, ActorAccount, Role, set_actor

from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp.views.json import register as register_json_views

from ..controllers.system import SystemController
from ..settings import BasicAuthSettings, DashboardSettings
from ..settings.auth import User

#: An Admin, for tests that look at a sub-controller and so skip the resolution of the actor. The name is the one of the
#: system account that authors the favourites recorded before there were accounts.
ADMIN_ACTOR = Actor(account=ActorAccount(id=None, username="anonymous", role=Role.ADMIN), role=Role.ADMIN, via="test")


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
            )
        finally:
            await system.dispose()


def parametrize_with_settings(*args):
    return pytest.mark.parametrize("controller", args, indirect=True)


def basic_admin_settings() -> DashboardSettings:
    """Settings of a dashboard with one Basic user, ``admin``, for tests that need to be let in without a database."""
    return DashboardSettings(
        auth=BasicAuthSettings(type="basic", algorithm="plaintext", users={"admin": User(password="admin")}),
        devserver={"enabled": True, "port": 5173},
    )


#: Headers that sign ``admin`` in with Basic, to go with :func:`basic_admin_settings` and :class:`RoleNamedActors`.
BASIC_ADMIN_HEADERS = {"authorization": "basic " + b64encode(b"admin:admin").decode()}


class RoleNamedActors:
    """Stands for the actor resolver: an account is named after its role, ``disabled`` is refused."""

    async def session(self, secret):
        return None

    async def basic(self, username):
        if username == "disabled":
            return None
        role = Role.parse(username)
        return Actor(account=ActorAccount(id=1, username=username, role=role), role=role, via="basic")


class AdminThroughASGIFixtureMixin(ControllerThroughASGIFixtureMixin):
    """The controller under test is a sub-controller of the dashboard, which is what resolves the actor: here it is an
    Admin."""

    @pytest.fixture
    def kernel(self, controller):
        async def as_admin(request):
            set_actor(request, ADMIN_ACTOR)
            return await controller(request)

        kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=as_admin), handle_errors=False)
        register_json_views(kernel.dispatcher)
        return kernel

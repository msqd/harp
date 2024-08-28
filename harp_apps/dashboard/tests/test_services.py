from copy import deepcopy

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.config.builders.system import System

from ..controllers.blobs import BlobsController
from ..settings import DashboardSettings


class BaseSystemTest:
    applications = []
    settings = {}

    async def create_system(self) -> System:
        return await ConfigurationBuilder(
            {
                "applications": self.applications,
                **deepcopy(self.settings),
            },
            use_default_applications=False,
        ).abuild_system()


class TestBlobsControllerService(BaseSystemTest):
    applications = ["http_client", "storage", "harp_apps.dashboard"]
    settings = {"dashboard": asdict(DashboardSettings(enable_ui=False))}

    async def test_get_instances(self):
        system = await self.create_system()

        # we can get an api controller for blobs-related stuff
        controller = system.provider.get("dashboard.controller.blobs")
        assert isinstance(controller, BlobsController)

        # the router is a singleton, for this application
        router = system.provider.get("dashboard.router")
        assert router is controller.router

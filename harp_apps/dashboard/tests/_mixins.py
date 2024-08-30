from copy import deepcopy

import pytest

from harp.config import ConfigurationBuilder
from harp.controllers import ProxyControllerResolver

from ..controllers.system import SystemController


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

        system = await ConfigurationBuilder(raw_settings, use_default_applications=False).abuild_system()

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

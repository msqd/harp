from typing import Optional

from harp.config import ConfigurationBuilder
from harp.config.builders.system import System


class BaseTestDefaultsWith:
    default_applications = ("http_client",)

    async def create_system(self, values: Optional[dict] = None, /, *, applications=None) -> System:
        applications = applications or self.default_applications
        config = ConfigurationBuilder({"applications": applications}, use_default_applications=False)
        if values is not None:
            config.add_values(values)
        return await config.abuild_system()

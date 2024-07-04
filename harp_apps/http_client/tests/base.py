from harp import Config
from harp.config.factories.kernel_factory import KernelFactory


class BaseTestDefaultsWith:
    default_applications = ("http_client",)

    async def build(self, /, *, applications=None):
        config = Config(applications=applications or self.default_applications)
        factory = KernelFactory(config)
        kernel, binds = await factory.build()
        return factory, kernel

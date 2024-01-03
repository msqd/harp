from harp import get_logger
from harp.factories.adapters.base import AbstractServerAdapter

logger = get_logger(__name__)


class GranianServerAdapter(AbstractServerAdapter):
    async def serve(self):
        """
        Creates and serves the proxy using granian.
        """
        from .granian_impl import Granian

        app = await self.wrapped.create()

        if len(self.wrapped.binds) != 1:
            raise NotImplementedError("Granian only supports one and exactly one bind.")

        server = Granian(app, self.wrapped.binds)
        server.serve()

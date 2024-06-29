from datetime import datetime, timedelta

from harp_apps.storage.types import IStorage

from .base import FacetWithStorage


class TransactionEndpointFacet(FacetWithStorage):
    name = "endpoint"

    def __init__(self, *, storage: IStorage):
        super().__init__(storage=storage)
        self.choices = set()
        self._refreshed_at = None

    async def refresh(self):
        if not self._refreshed_at or (self._refreshed_at < datetime.now() - timedelta(seconds=25)):
            self._refreshed_at = datetime.now()
            meta = await self.storage.get_facet_meta(self.name)
            self.choices = set(meta.keys())
            self.meta = {endpoint: {"count": count} for endpoint, count in meta.items()}

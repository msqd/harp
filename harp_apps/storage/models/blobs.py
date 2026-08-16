from sqlalchemy import TIMESTAMP, LargeBinary, String, delete, func, select
from sqlalchemy.orm import aliased, mapped_column

from harp.models import Blob as BlobModel

from .base import Base, Repository, with_session
from .messages import Message


class Blob(Base):
    __tablename__ = "blobs"

    id = mapped_column(String(40), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class BlobsRepository(Repository[Blob]):
    Type = Blob

    def _orphans_subquery(self):
        """Blobs paired with the number of messages referencing them, so zero means unreferenced."""
        MH = aliased(Message, name="mh")
        MB = aliased(Message, name="mb")
        return (
            select(Blob.id, func.count(MH.id) + func.count(MB.id))
            .select_from(Blob)
            .outerjoin(MH, MH.headers == Blob.id)
            .outerjoin(MB, MB.body == Blob.id)
            .group_by(Blob.id)
            .subquery()
        )

    def count_orphans(self):
        subquery = self._orphans_subquery()
        return select(func.count(subquery.c.id)).where(subquery.c[1] == 0)

    def select_orphans(self):
        """The ids `delete_orphans` would remove.

        Deleting blobs with a bulk statement leaves anything caching their existence, such as
        `SqlBlobStorage.seen`, believing rows are there that are not. The caller needs to know
        which ids went, so the count, the selection and the deletion all read from one definition
        of "orphan" and cannot drift apart.
        """
        subquery = self._orphans_subquery()
        return select(subquery.c.id).where(subquery.c[1] == 0)

    def delete_orphans(self):
        return delete(Blob).where(Blob.id.in_(self.select_orphans()))

    @with_session
    async def create(self, values: dict | BlobModel, /, *, session):
        if isinstance(values, BlobModel):
            values = dict(
                id=values.id,
                data=values.data,
                content_type=values.content_type,
            )
        return await super().create(values, session=session)

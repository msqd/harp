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

    def count_orphans(self):
        MH = aliased(Message, name="mh")
        MB = aliased(Message, name="mb")
        subquery = (
            select(Blob.id, func.count(MH.id) + func.count(MB.id))
            .select_from(Blob)
            .outerjoin(MH, MH.headers == Blob.id)
            .outerjoin(MB, MB.body == Blob.id)
            .group_by(Blob.id)
            .subquery()
        )
        query = select(func.count(subquery.c.id)).where(subquery.c[1] == 0)
        return query

    def delete_orphans(self):
        MH = aliased(Message, name="mh")
        MB = aliased(Message, name="mb")
        subquery = (
            select(Blob.id, func.count(MH.id) + func.count(MB.id))
            .select_from(Blob)
            .outerjoin(MH, MH.headers == Blob.id)
            .outerjoin(MB, MB.body == Blob.id)
            .group_by(Blob.id)
            .subquery()
        )
        query = select(subquery.c.id).where(subquery.c[1] == 0)
        return delete(Blob).where(Blob.id.in_(query))

    @with_session
    async def create(self, values: dict | BlobModel, /, *, session):
        if isinstance(values, BlobModel):
            values = dict(
                id=values.id,
                data=values.data,
                content_type=values.content_type,
            )
        return await super().create(values, session=session)

from sqlalchemy import LargeBinary, String, func, select
from sqlalchemy.orm import aliased, mapped_column

from .base import Base, Repository
from .messages import Message


class Blob(Base):
    __tablename__ = "sa_blobs"

    id = mapped_column(String(40), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))


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

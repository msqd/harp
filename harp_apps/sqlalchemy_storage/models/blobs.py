from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import mapped_column

from .base import Base


class Blob(Base):
    __tablename__ = "sa_blobs"

    id = mapped_column(String(40), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))

from sqlalchemy.ext.asyncio import create_async_engine

from harp.contrib.sqlalchemy_storage.settings import HARP_SQLALCHEMY_STORAGE

engine = create_async_engine(HARP_SQLALCHEMY_STORAGE["database"], echo=True)

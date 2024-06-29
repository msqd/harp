from datetime import UTC, datetime

from harp.models import Blob, Message, Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.sqlalchemy_storage.storages.sql import SqlStorage
from harp_apps.sqlalchemy_storage.types import IBlobStorage


class SqlalchemyStorageTestFixtureMixin:
    async def create_transaction(self, storage: SqlStorage, **kwargs):
        return await storage.transactions.create(
            Transaction(
                **{
                    **{
                        "id": generate_transaction_id_ksuid(),
                        "type": "http",
                        "endpoint": "/",
                        "started_at": datetime.now(UTC),
                    },
                    **kwargs,
                }
            )
        )

    async def create_blob(self, blob_storage: IBlobStorage, data, /, **kwargs):
        return await blob_storage.put(Blob.from_data(data, **kwargs))

    async def create_message(self, storage: SqlStorage, **kwargs):
        return await storage.messages.create(Message(**kwargs))

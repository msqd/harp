from datetime import UTC, datetime

from harp.models import Blob, Message, Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage


class StorageTestFixtureMixin:
    async def create_transaction(self, sql_storage: SqlStorage, **kwargs):
        return await sql_storage.transactions.create(
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

    async def create_message(self, sql_storage: SqlStorage, **kwargs):
        return await sql_storage.messages.create(Message(**kwargs))

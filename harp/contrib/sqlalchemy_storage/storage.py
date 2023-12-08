from sqlalchemy import alias, select

from harp.contrib.sqlalchemy_storage.engine import engine
from harp.contrib.sqlalchemy_storage.tables import BlobsTable, MessagesTable, TransactionsTable
from harp.core.models.messages import Blob, Message
from harp.core.models.transactions import Transaction

transactions = alias(TransactionsTable, name="t")
messages = alias(MessagesTable, name="m")
LEN_TRANSACTIONS_COLUMNS = len(TransactionsTable.columns)


class SqlAlchemyStorage:
    async def find_transactions(self, *, with_messages=False):
        query = select(transactions, messages)
        if with_messages:
            # query.add_columns(messages)
            query = query.outerjoin(messages, messages.c.transaction_id == transactions.c.id)
        query = query.order_by(transactions.c.started_at.desc()).limit(50)

        current_transaction = None
        async with engine.connect() as conn:
            result = await conn.execute(query)
            for row in result.fetchall():
                # not the same transaction, build new one
                if current_transaction is None or current_transaction.id != row[0]:
                    _db_transaction = row[0:LEN_TRANSACTIONS_COLUMNS]
                    if current_transaction:
                        yield current_transaction
                    current_transaction = Transaction(
                        id=_db_transaction[0],
                        type=_db_transaction[1],
                        started_at=_db_transaction[2],
                        finished_at=_db_transaction[3],
                        ellapsed=_db_transaction[4],
                        messages=[],
                    )

                if with_messages and row[LEN_TRANSACTIONS_COLUMNS]:
                    _db_message = row[LEN_TRANSACTIONS_COLUMNS:]
                    current_transaction.messages.append(
                        Message(
                            id=_db_message[0],
                            transaction_id=_db_message[1],
                            kind=_db_message[2],
                            summary=_db_message[3],
                            headers=_db_message[4],
                            body=_db_message[5],
                            created_at=_db_message[6],
                        )
                    )

            if current_transaction:
                yield current_transaction

    async def get_blob(self, blob_id):
        """
        Retrieve a blob from the database, using its hash.
        Returns None if not found.

        :param blob_id: sha1 hash of the blob
        :return: Blob or None
        """
        async with engine.connect() as conn:
            row = (await conn.execute(BlobsTable.select().where(BlobsTable.c.id == blob_id))).fetchone()

        if row:
            return Blob(id=row.id, data=row.data)

from harp.core.models.transactions import Transaction


class SqlAlchemyStorage:
    async def find_transactions(self):
        from harp.contrib.sqlalchemy_storage.engine import engine
        from harp.contrib.sqlalchemy_storage.tables import TransactionsTable

        async with engine.begin() as conn:
            async for row in await conn.stream(
                TransactionsTable.select().order_by(TransactionsTable.c.started_at.desc()).limit(50)
            ):
                yield Transaction(
                    id=row.id,
                    type=row.type,
                    started_at=row.started_at,
                    finished_at=row.finished_at,
                    ellapsed=row.ellapsed,
                )

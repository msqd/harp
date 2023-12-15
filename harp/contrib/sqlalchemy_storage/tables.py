from sqlalchemy import BLOB, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table

metadata = MetaData()

# todo endpoint name + api
TransactionsTable = Table(
    "sa_transactions",
    metadata,
    Column("id", String(27), primary_key=True, unique=True),
    Column("type", String(10)),
    Column("endpoint", String(32), nullable=True),
    Column("started_at", DateTime()),
    Column("finished_at", DateTime(), nullable=True),
    Column("elapsed", Float(), nullable=True),
)

BlobsTable = Table(
    "sa_blobs",
    metadata,
    Column("id", String(40), primary_key=True, unique=True),
    Column("data", BLOB()),
)

MessagesTable = Table(
    "sa_messages",
    metadata,
    Column("id", Integer(), primary_key=True, unique=True, autoincrement=True),
    Column("transaction_id", String(27), ForeignKey("sa_transactions.id")),
    Column("kind", String(10)),
    Column("summary", String(255)),
    Column("headers", String(40), ForeignKey("sa_blobs.id")),
    Column("body", String(40), ForeignKey("sa_blobs.id")),
    Column("created_at", DateTime()),
)


async def create_all_tables(engine, *, drop_tables=False):
    async with engine.begin() as conn:
        if drop_tables:
            await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from docs._captures.seed import NOW, build_transactions, seed
from harp_apps.storage.models import Base


def describe(transactions):
    return [(t.id, t.endpoint, t.started_at, t.elapsed, t.extras, request) for t, request in transactions]


def test_seed_data_is_the_same_on_every_call():
    assert describe(build_transactions()) == describe(build_transactions())


def test_seed_data_lies_in_the_past_of_the_frozen_clock():
    assert all(transaction.finished_at <= NOW for transaction, _ in build_transactions())


def test_seed_writes_transactions_with_both_messages(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'harp.db'}"

    async def run():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        await seed(url)
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            transactions = (await conn.execute(text("select count(*) from transactions"))).scalar()
            messages = (await conn.execute(text("select count(*) from messages"))).scalar()
        await engine.dispose()
        return transactions, messages

    transactions, messages = asyncio.run(run())

    assert messages == 2 * transactions == 2 * len(list(build_transactions()))

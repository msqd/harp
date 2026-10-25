from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from harp.settings import PAGE_SIZE
from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.errors import StorageTimeLimitExceeded
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)


def ids(result):
    return [t.id for t in result]


class TestTransactionListPeriod(StorageTestFixtureMixin):
    async def at(self, sql_storage: SqlStorage, minutes: int, **kwargs):
        return await self.create_transaction(sql_storage, started_at=T0 + timedelta(minutes=minutes), **kwargs)

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_period_is_closed_on_from_and_open_on_to(self, sql_storage: SqlStorage):
        before = await self.at(sql_storage, -1)
        first = await self.at(sql_storage, 0)
        inside = await self.at(sql_storage, 5)
        last = await self.at(sql_storage, 9)
        at_to = await self.at(sql_storage, 10)

        result = await sql_storage.get_transaction_list(username="anonymous", from_=T0, to=T0 + timedelta(minutes=10))

        assert set(ids(result)) == {first.id, inside.id, last.id}
        assert result.meta["total"] == 3
        assert before.id not in ids(result) and at_to.id not in ids(result)

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_either_bound_is_optional(self, sql_storage: SqlStorage):
        early = await self.at(sql_storage, -5)
        late = await self.at(sql_storage, 5)

        only_from = await sql_storage.get_transaction_list(username="anonymous", from_=T0)
        only_to = await sql_storage.get_transaction_list(username="anonymous", to=T0)

        assert ids(only_from) == [late.id]
        assert ids(only_to) == [early.id]

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_naive_bounds_are_utc(self, sql_storage: SqlStorage):
        inside = await self.at(sql_storage, 5)
        await self.at(sql_storage, 15)

        result = await sql_storage.get_transaction_list(
            username="anonymous", from_=T0.replace(tzinfo=None), to=(T0 + timedelta(minutes=10)).replace(tzinfo=None)
        )

        assert ids(result) == [inside.id]

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_bounds_in_another_timezone_are_converted(self, sql_storage: SqlStorage):
        inside = await self.at(sql_storage, 5)
        await self.at(sql_storage, 15)
        plus_two = timezone_plus(2)

        result = await sql_storage.get_transaction_list(
            username="anonymous",
            from_=T0.astimezone(plus_two),
            to=(T0 + timedelta(minutes=10)).astimezone(plus_two),
        )

        assert ids(result) == [inside.id]

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_newest_first_with_cursor_pages(self, sql_storage: SqlStorage):
        # transaction ids are time-ordered (ksuid), the cursor relies on it
        created = [await self.at(sql_storage, minute, id=f"tx{minute:02d}".ljust(27, "0")) for minute in range(5)]
        newest_first = [t.id for t in reversed(created)]

        first = await sql_storage.get_transaction_list(username="anonymous", from_=T0)
        after = await sql_storage.get_transaction_list(username="anonymous", from_=T0, cursor=newest_first[2])

        assert ids(first) == newest_first
        assert ids(after) == newest_first[2:]

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_period_combines_with_filters_text_and_pagination(self, sql_storage: SqlStorage):
        for minute in range(PAGE_SIZE + 3):
            await self.at(sql_storage, minute, endpoint="/billing")
        await self.at(sql_storage, -30, endpoint="/billing")
        await self.at(sql_storage, 5, endpoint="/other")

        kwargs = dict(
            username="anonymous",
            from_=T0,
            to=T0 + timedelta(minutes=PAGE_SIZE + 3),
            filters={"endpoint": ["/billing"]},
            text_search="bill",
        )
        first = await sql_storage.get_transaction_list(**kwargs)
        second = await sql_storage.get_transaction_list(page=2, **kwargs)

        assert first.meta["total"] == PAGE_SIZE + 3
        assert len(first) == PAGE_SIZE
        assert len(second) == 3

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_text_search_never_matches_outside_the_period(self, sql_storage: SqlStorage):
        outside = await self.at(sql_storage, -60, endpoint="/a")
        await self.create_message(
            sql_storage, transaction_id=outside.id, kind="request", summary="needle", headers="h", body="b"
        )
        inside = await self.at(sql_storage, 1, endpoint="/b")
        await self.create_message(
            sql_storage, transaction_id=inside.id, kind="request", summary="needle", headers="h", body="b"
        )

        result = await sql_storage.get_transaction_list(
            username="anonymous", from_=T0, to=T0 + timedelta(hours=1), text_search="needle"
        )

        assert ids(result) == [inside.id]
        assert result.meta["total"] == 1

    @parametrize_with_database_urls("sqlite")
    async def test_text_search_runs_inside_the_period_index_range(self, sql_storage: SqlStorage):
        """On SQLite the plan shows transactions are located through the ``started_at`` index before messages are
        probed, which is what bounds the text search."""
        plan = await explain(
            sql_storage,
            from_=T0,
            to=T0 + timedelta(hours=1),
            text_search="needle",
        )

        assert any("transactions" in row and "ix_transactions_started_at" in row and "SEARCH" in row for row in plan)


class TestTransactionListTimeLimit(StorageTestFixtureMixin):
    @parametrize_with_database_urls("sqlite")
    async def test_generous_limit_returns_results(self, sql_storage: SqlStorage):
        t = await self.create_transaction(sql_storage)

        result = await sql_storage.get_transaction_list(username="anonymous", time_limit=30)

        assert ids(result) == [t.id]

    @parametrize_with_database_urls("sqlite")
    async def test_exceeded_limit_raises_dedicated_error(self, sql_storage: SqlStorage):
        await self.create_transaction(sql_storage)

        with pytest.raises(StorageTimeLimitExceeded):
            await sql_storage.get_transaction_list(username="anonymous", time_limit=1e-9)


def timezone_plus(hours: int):
    from datetime import timezone

    return timezone(timedelta(hours=hours))


async def explain(sql_storage: SqlStorage, **kwargs) -> list[str]:
    """Plan of the list query, captured through the debugging instrumentation."""
    sql_storage.install_debugging_instrumentation()
    await sql_storage.get_transaction_list(username="anonymous", **kwargs)
    select_sql = next(q for q in sql_storage.sql_queries if "LIMIT" in q)
    async with sql_storage.begin() as session:
        rows = (await session.execute(text("EXPLAIN QUERY PLAN " + select_sql))).fetchall()
    return [str(row) for row in rows]

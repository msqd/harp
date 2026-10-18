import pytest
from sqlalchemy import insert

from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.utils.upsert import execute_in_chunks, insert_ignoring_duplicates


class FakeConnection:
    def __init__(self):
        self.calls = []

    async def execute(self, statement, rows):
        self.calls.append(rows)


async def test_rows_go_in_chunks():
    conn = FakeConnection()
    rows = [{"n": n} for n in range(250)]

    await execute_in_chunks(conn, insert(SqlBlob), rows, size=100)

    assert [len(call) for call in conn.calls] == [100, 100, 50]
    assert [row for call in conn.calls for row in call] == rows


async def test_no_rows_no_statement():
    conn = FakeConnection()
    await execute_in_chunks(conn, insert(SqlBlob), [])
    assert conn.calls == []


@pytest.mark.parametrize(
    "dialect, expected",
    [
        ("postgresql", "ON CONFLICT (id) DO NOTHING"),
        ("sqlite", "ON CONFLICT (id) DO NOTHING"),
        ("mysql", "ON DUPLICATE KEY UPDATE id = blobs.id"),
    ],
)
def test_duplicates_are_left_alone_on_every_dialect(dialect, expected):
    from sqlalchemy.dialects import mysql, postgresql, sqlite

    statement = insert_ignoring_duplicates(dialect, SqlBlob.__table__)
    compiled = str(
        statement.compile(dialect={"postgresql": postgresql, "sqlite": sqlite, "mysql": mysql}[dialect].dialect())
    )
    assert expected in compiled

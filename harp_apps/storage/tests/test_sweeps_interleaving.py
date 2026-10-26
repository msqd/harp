"""A janitor pass must give the connection back between batches (#1215).

The default in-memory SQLite database has one connection: a pass holding it for its whole scan
stalls every request that needs the database.
"""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import insert, select

from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.tests import sweeps_with_grace
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage

BLOBS = 3000


@pytest.mark.parametrize("pass_name", ["delete_orphan_blobs", "compute_and_store_metrics"])
async def test_request_completes_while_a_pass_is_running(
    sql_storage: SqlStorage, blob_storage: IBlobStorage, pass_name: str
):
    if blob_storage.type != "sql":
        pytest.skip("The janitor only sweeps SQL blob storage.")
    worker = sweeps_with_grace(sql_storage, blob_storage, timedelta(0))
    async with sql_storage.session_factory() as session:
        await session.execute(insert(SqlBlob), [{"id": f"{i:040d}", "data": b"x"} for i in range(BLOBS)])
        await session.commit()

    sweep = asyncio.create_task(getattr(worker, pass_name)())
    served_during_sweep = 0
    while not sweep.done():
        async with sql_storage.session_factory() as session:
            await asyncio.wait_for(session.execute(select(1)), timeout=10)
        served_during_sweep += not sweep.done()
    await sweep

    assert served_during_sweep > 1

from datetime import datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import MissingGreenlet, StatementError
from sqlalchemy.orm.exc import DetachedInstanceError

from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestModelsBase(StorageTestFixtureMixin):
    async def test_create_using_explicit_session(self, sql_storage: SqlStorage):
        """
        Check how instance creation works with an explicit session scope created outside the "create" call.

        """
        async with sql_storage.session_factory() as session:
            # we create a transaction with our own session
            db_transaction = await sql_storage.transactions.create(
                {
                    "id": generate_transaction_id_ksuid(),
                    "type": "http",
                    "endpoint": "/api/transactions",
                    "started_at": datetime.now(),
                },
                session=session,
            )

            # but lazy loading cannot work there ...
            with pytest.raises((MissingGreenlet, StatementError)):
                _ = db_transaction._tag_values

            # ... unless we use the async wrapper ...
            assert await db_transaction.awaitable_attrs._tag_values == []

            # ... and after that, the attribute is now populated
            assert db_transaction._tag_values == []

            # within the session, the object is not detached nor expired
            assert inspect(db_transaction).detached is False
            assert inspect(db_transaction).expired is False

        # although it will be dettached once the session is closed
        assert inspect(db_transaction).detached is True
        assert inspect(db_transaction).expired is False

    async def test_create_using_inplicit_session(self, sql_storage: SqlStorage):
        """
        Check how instance creation works with an implicit session.

        """
        # we create a transaction without an explicit session
        db_transaction = await sql_storage.transactions.create(
            {
                "id": generate_transaction_id_ksuid(),
                "type": "http",
                "endpoint": "/api/transactions",
                "started_at": datetime.now(),
            },
        )

        # we cannot lazy load on a detached instance ...
        with pytest.raises(DetachedInstanceError):
            _ = db_transaction._tag_values

        # ... not even with the async wrapper
        with pytest.raises(DetachedInstanceError):
            _ = await db_transaction.awaitable_attrs._tag_values

        # we can see it is (correctly) detached
        assert inspect(db_transaction).detached is True
        assert inspect(db_transaction).expired is False

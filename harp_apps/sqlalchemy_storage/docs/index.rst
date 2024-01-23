SQLAlchemy Storage
==================

The `harp.contrib.sqlalchemy_storage` application implements database storage using SQLAlchemy with asynchronous
engines.

External documentation:

- `SQLAlchemy <https://www.sqlalchemy.org/>`_
- `aiosqlite <https://aiosqlite.omnilib.dev/>`_
- `asyncpg <https://magicstack.github.io/asyncpg/>`_

Configuration
:::::::::::::

SQLite
------

SQLite has the benefit of requiring no external service, and is thus the default storage engine.
Do not use it in production, as it is slow and have concurrency issues.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: sqlite+aiosqlite:///harp.db
          drop_tables: false
          echo: false


PostgreSQL
----------

PostgreSQL is the recommended storage engine for production use.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: postgresql+asyncpg://user:password@localhost:5432/harp
          drop_tables: false
          echo: false

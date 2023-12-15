Storage
=======

.. versionadded:: 0.2

Some features (including the dashboard) requires a storage engine to be configured.

Current storage implementation relies on `SQLAlchemy <https://www.sqlalchemy.org/>`_, using its asynchronous API. The
only tested engines are sqlite (using `aiosqlite <https://aiosqlite.omnilib.dev/>`_) and postgresql (using
`asyncpg <https://magicstack.github.io/asyncpg/>`_).

SQLite
::::::

SQL has the benefit of requiring no external service, and is thus the default storage engine.
Do not use it in production, as it is slow and have concurrency issues.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: sqlite+aiosqlite:///harp.db
          drop_tables: false
          echo: false


PostgreSQL
::::::::::

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: postgresql+asyncpg://user:password@localhost:5432/harp
          drop_tables: false
          echo: false

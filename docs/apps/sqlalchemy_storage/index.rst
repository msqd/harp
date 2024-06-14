SQLAlchemy Storage
==================

The `harp.contrib.sqlalchemy_storage` application implements database storage using SQLAlchemy with asynchronous
engines. The test suites runs against SQLite, PostgreSQL and MySQL, using various implementations. Other drivers
may work too, but are not tested.

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


PostgreSQL
----------

PostgreSQL is the recommended storage engine for production use.

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: postgresql+asyncpg://user:password@localhost:5432/harp

MySQL
-----

MySQL / MariaDB is another option for production use.

Using aiomysql:

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: mysql+aiomysql://user:password@localhost:3306/harp

Using asyncmy:

.. tab-set-code::

    .. code-block:: yaml

        storage:
          type: sqlalchemy
          url: mysql+asyncmy://user:password@localhost:3306/harp


Common options
--------------


Drop tables
...........

To drop and recreate all tables, use ``--reset``. It will attempt to drop all tables before running the migrations.

.. code-block:: bash

    harp start ... --reset


Logging
.......

To instruct SQLAlchemy to log all queries, set ``LOGGING_SQLALCHEMY=INFO`` in your env.

.. code-block:: shell

    LOGGING_SQLALCHEMY=INFO harp start ...

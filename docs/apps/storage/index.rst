Storage
=======

.. tags:: applications

.. versionadded:: 0.5

.. versionchanged:: 0.6

    * The ``harp_apps.storage`` application was previously named ``harp_apps.sqlalchemy_storage``.
    * The blob storage system was added, and now supports both SQL or Redis backends.
    * the ``storage.type`` was removed, because there was only one valid value.

The ``harp_apps.storage`` application implements various storage systems for your proxies to use.

.. toctree::
    :hidden:
    :maxdepth: 1

    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.storage>

There are two different storage kinds:

- **Transaction/Core storage**: Currently SQL-only, the core storage will handle persisting the transactions and
  messages, along with a few other utilities like users, tags, flags ... The core storage implements the
  :class:`IStorage <harp_apps.storage.types.storage.IStorage>` interface.
- **Blobs storage**: The blobs storage is a separate storage system that stores the binary content of the messages. It
  is used to store the headers and the body of the requests and responses. The blobs storage implements the
  :class:`IBlobStorage <harp_apps.storage.types.blob_storage.IBlobStorage>` interface. The blob storage is
  `content-addressable <https://en.wikipedia.org/wiki/Content-addressable_storage>`_, so that multiple indentical blobs
  are stored only once.

By default, blob storage will use the same SQL database as the core storage, but you can configure it to use a different
underlying system (for now, the only alternative is Redis, but the simple interface allows for easy addition of new
backends for blobs).


Core storage
::::::::::::

The core storage leverages `SQLAlchemy <https://www.sqlalchemy.org/>`_ to store the transactions in a SQL database.

We officially support the following SQL databases (although any async SQLAlchemy-supported database should work, they
are not included in the test suite and may bring unexpected behaviours):

- `SQLite <https://www.sqlite.org/>`_ (config-less default, **do not use for production**), using `aiosqlite
  <https://aiosqlite.omnilib.dev/>`_ driver.
- `PostgreSQL <https://www.postgresql.org/>`_ (our favorite choice for production), using `asyncpg
  <https://magicstack.github.io/asyncpg/>`_ driver.
- `MySQL <https://www.mysql.com/>`_ / `MariaDB <https://mariadb.org/>`_, using `aiomysql
  <https://aiomysql.readthedocs.io/>`_ or `asyncmy <https://github.com/long2ice/asyncmy>`_ driver.


Configuration
-------------

Storages are configured under the ``storage`` key of the configuration, and the settings implementation is backed by
:class:`StorageSettings <harp_apps.storage.settings.StorageSettings>`.

The main configuration option you're interested in is ``storage.url``, which configure the target SQL server.

**PostgreSQL example (asyncpg driver)**:

.. literalinclude:: ./examples/postgres-asyncpg.yml
    :language: yaml

**MySQL/MariaDB example (aiomysql driver)**:

.. literalinclude:: ./examples/mysql-aiomysql.yml
    :language: yaml

**MySQL/MariaDB example (asyncmy driver)**:

.. literalinclude:: ./examples/mysql-asyncmy.yml
    :language: yaml

**SQLite example (aiosqlite driver)**:

SQLite is the default storage engine because requires no configuration. *Do not use it in production*. It is slow and
has concurrency issues. It is only suitable (and handy) for development and testing.

.. literalinclude:: ./examples/sqlite-aiosqlite.yml
    :language: yaml


Blob storage
::::::::::::

Without configuration, the blob storage will use the same SQL database as the core storage. For intensive production
use, we suggest you switch the underlying implementation to a Redis-based one. The test suite only runs against the
official redis docker image, but we'll add tested support for alternatives, like KeyDB or Valkey in the future.


Configuration
-------------

To setup a redis-based blob storage, you can add the following to your configuration:

**Redis example**:

.. literalinclude:: ./examples/redis.yml
    :language: yaml


Migrations
::::::::::

By default, migrations are run averytime you start HARP, to ensure the database schema is always up-to-date.

You can disable this behaviour by adding ``storage.migrate = false`` to your configuration.

Migrations are implemented using `Alembic <https://alembic.sqlalchemy.org/>`_.


Resetting
:::::::::

If you want to reset the storage content, you can run the ``harp db:reset`` command. It will drop all tables,
then run the migrations again (if enabled), so that you get an empty and up-to-date database schema.

You must provide your configuration files and configuration arguments to this command, like you'd do with the
``harp start`` command, so that it points to the right storage.

.. code-block:: shell

    harp db:reset -f /path/to/config.yml

or...

.. code-block:: shell

    harp db:reset --set storage.url=...


Logging
:::::::

To instruct SQLAlchemy to log all queries, set ``LOGGING_SQLALCHEMY=INFO`` in your env.

.. code-block:: shell

    LOGGING_SQLALCHEMY=INFO harp start ...

It works with all HARP commands, not just ``start``.

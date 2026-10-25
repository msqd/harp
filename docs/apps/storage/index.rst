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

    Transaction Markers <markers>
    Redaction <redaction>
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

.. warning::

    **Recording here is best-effort.** Transactions passing through HARP are recorded, including
    requests carrying ``Cache-Control: no-store`` (without their payload), but under load the storage worker sheds message
    detail first and then whole transactions rather than slowing traffic down. Do not treat this
    store as a complete account of what crossed the proxy. See :ref:`what-harp-retains` for what is
    measured, and `#945 <https://github.com/msqd/harp/issues/945>`_ for the measurements.

    A caller's ``Cache-Control: no-store`` binds the cache and, from 0.13, suppresses the headers and
    bodies recorded here, for the request and for the response; the transaction and its messages are
    still recorded, with their summaries. An origin's ``no-store`` suppresses its own response payload
    only. HARP does not currently provide a way to override this. See :ref:`what-harp-retains`.

    Choosing what is not recorded is currently the operator's decision, made with the
    :doc:`rules application </apps/rules/index>` and the :doc:`markers` below.


Core storage
::::::::::::

The core storage leverages `SQLAlchemy <https://www.sqlalchemy.org/>`_ to store the transactions in a SQL database.

HARP works with the following SQL databases. ``storage.url`` accepts only these schemes (``postgresql``,
``postgresql+asyncpg``, ``sqlite``, ``sqlite+aiosqlite``, ``mysql``, ``mysql+aiomysql``), any other is refused at
startup:

- `PostgreSQL <https://www.postgresql.org/>`_ (**the production database**), using `asyncpg
  <https://magicstack.github.io/asyncpg/>`_ driver. It is the only database we support in production and benchmark
  against.
- `SQLite <https://www.sqlite.org/>`_ (config-less default, **for development only**), using `aiosqlite
  <https://aiosqlite.omnilib.dev/>`_ driver.
- `MySQL <https://www.mysql.com/>`_ / `MariaDB <https://mariadb.org/>`_, using `aiomysql
  <https://aiomysql.readthedocs.io/>`_ driver. MariaDB uses the same ``mysql+aiomysql://`` URL. **Deprecated**, see below.

.. deprecated:: 0.12

   MySQL and MariaDB keep working and stay tested in CI, but come with no production support and no performance
   commitment, and will be removed in a future version (not decided yet). HARP logs a deprecation warning at boot
   when ``storage.url`` points to one of them. Use PostgreSQL for production.

SQLite ships with the base install. The PostgreSQL and MySQL drivers are extras, install the one you need:

.. code-block:: shell

    pip install harp-proxy[postgresql]  # asyncpg
    pip install harp-proxy[mysql]       # aiomysql, with cryptography

Without it, a ``storage.url`` for that database fails at startup with the extra to install.


Configuration
-------------

Storages are configured under the ``storage`` key of the configuration, and the settings implementation is backed by
:class:`StorageSettings <harp_apps.storage.settings.StorageSettings>`.

The main configuration option you're interested in is ``storage.url``, which configure the target SQL server.

**PostgreSQL example (asyncpg driver)**:

.. literalinclude:: ./examples/postgres-asyncpg.yml
    :language: yaml

**MySQL/MariaDB example (aiomysql driver, deprecated)**:

.. literalinclude:: ./examples/mysql-aiomysql.yml
    :language: yaml

**SQLite example (aiosqlite driver, development only)**:

SQLite is the default storage engine because requires no configuration. *Do not use it in production*. It is slow and
has concurrency issues. It is only suitable (and handy) for development and testing.

The default URL, ``sqlite+aiosqlite:///:memory:?cache=shared``, keeps the database in memory: it is lost at
shutdown, and it lives in a single connection that database operations take in turn, so they never run in
parallel. Point ``storage.url`` at a file to keep the data across restarts.

A file database runs in write-ahead log mode (``journal_mode=WAL``, ``synchronous=NORMAL``) with a 10 s
``busy_timeout``, set on every connection. Readers no longer wait for the writer, which removes the multi-second
stalls the default rollback journal caused under concurrent requests. This adds ``-wal`` and ``-shm`` files next to the
database (keep them with it when copying), and the file must be on a local filesystem: WAL does not work over network
filesystems. A single writer remains: writes still queue, and a lock held longer than the timeout raises
``database is locked``.

.. literalinclude:: ./examples/sqlite-aiosqlite.yml
    :language: yaml


Blob storage
::::::::::::

Without configuration, the blob storage uses the same SQL database as the core storage. PostgreSQL is the recommended
production setup. Redis is a supported option when you want to keep bodies and headers out of the SQL database. The test
suite only runs against the official redis docker image, but we'll add tested support for alternatives, like KeyDB or
Valkey in the future.

Retention differs per blob backend, see :doc:`/apps/janitor/index`:

- ``sql``: the janitor deletes the blobs nothing references anymore.
- ``redis``: same, by scanning the keys. Blobs carry no TTL, as they are shared between transactions and the HTTP
  cache. Each write also leaves a short-lived ``harp:blob-written:<id>`` marker key that protects fresh blobs from the
  sweep.
- ``memory``: same, and the blobs are lost on restart anyway.


Configuration
-------------

To setup a redis-based blob storage, you can add the following to your configuration:

**Redis example**:

.. literalinclude:: ./examples/redis.yml
    :language: yaml


.. _storage-recording-capacity:

Recording capacity
::::::::::::::::::

The storage worker runs its writes one at a time, in the order they are queued. A recorded request
costs about 8 jobs: the transaction, its end, and a message, a headers blob and a body blob for each
of the request and the response.

On PostgreSQL 16, the worker drains about 150 to 400 jobs per second, so HARP records about **20 to
45 requests per second in full**. Measured on a shared 6 vCPU host running the proxy, the upstream,
the load generator and PostgreSQL in Docker: the bound is the proxy's CPU (one Python event loop)
more than the database, which commits in about 1 ms. To estimate yours, divide the drain rate you
observe (the fall of ``async_worker_queue_backlog`` per second once traffic stops) by 8.

Above that rate, the queue grows and the worker sheds, by backlog size:

============= ====================================================
Backlog       Not recorded
============= ====================================================
100 jobs      request and response bodies (``shed-bodies``)
1,000 jobs    messages (``shed-messages``)
10,000 jobs   whole transactions
============= ====================================================

A level engages only once the backlog has stayed at or above it for 2 seconds, so a burst the worker
absorbs within 2 seconds is recorded in full. It stops as soon as the backlog falls below the level
again. Just above the capacity, only some bodies are lost: in one run at 50 requests per second for
a minute, 339 of 3,000 transactions were recorded without bodies. Messages, then whole transactions,
go when the database falls far behind, for instance when it stalls. Proxied traffic is not slowed
down by shedding (one exception: a stalled database shared with the http cache, `#1352
<https://github.com/msqd/harp/issues/1352>`_, see :doc:`/operate/upgrading`).

There is no hysteresis: a level switches on after the 2 second hold and off the moment the backlog
drops below its threshold. On a slow, not stalled, database whose backlog hovers around 1,000 jobs,
message shedding therefore switches on and off, and messages drop in bursts rather than evenly. See :ref:`storage-load-shedding` for the warning and the metrics that report it.

.. _storage-memory-sizing:

Memory under recording backlog
------------------------------

Queued jobs hold their bodies in memory, up to 1 MiB each for the request and the response, until the
worker writes them. Bodies are shed from 100 jobs, but jobs already queued keep theirs, and the queue
only stops growing at the last level: 10,000 jobs, after the 2 second hold. The backlog, so the memory, is
bounded by that level. The worst case, with every request and response body at the 1 MiB cap, is::

    memory ≈ base + (10,000 jobs / 8 jobs per request) × (request body + response body)
           ≈ base + 1,250 × 2 MiB ≈ base + 2.5 GiB

Smaller bodies scale it down linearly: with 10 KiB bodies the backlog holds about 25 MiB of bodies.
Measured: 32 clients POSTing 1 MiB bodies against a paused PostgreSQL, the proxy grew from 109 MB to a
plateau of 1,670 MB. Size the memory limit of the container for the formula with your own body sizes, not
for the base footprint.


Migrations
::::::::::

By default, migrations are run every time you start HARP, to ensure the database schema is always
up-to-date. On that default, upgrading HARP and starting it is enough, and there is nothing to run by
hand.

You can disable this behaviour by setting ``storage.migrate`` to ``false`` in your configuration.
Applying migrations then becomes yours to do, with ``harp-proxy db:migrate up head``, **before**
starting the new version. A schema older than the running code is not a degraded mode: 0.10 widened
``blobs.id`` for cache keys, and against a database still holding the narrow column, any response the
cache would store fails with a 500 rather than falling back to a cache miss.

HARP checks the schema at every start and refuses to boot, with a fatal error and a non-zero exit code, if it
is older than the code expects. The error names the database and the commands to run.

SQLite files are not migrated: they are created from the models and never altered. A SQLite file written by
0.11 lacks ``transactions.markers``, so it must be deleted (it is recreated on next start) or reset with
``harp-proxy db:reset``. PostgreSQL (and the deprecated MySQL) are migrated automatically at boot, unless ``storage.migrate`` is ``false``,
in which case ``harp-proxy db:migrate up head`` is yours to run.

Migrations are implemented using `Alembic <https://alembic.sqlalchemy.org/>`_.


Resetting
:::::::::

If you want to reset the storage content, you can run the ``harp-proxy db:reset`` command. It will drop all tables,
then run the migrations again (if enabled), so that you get an empty and up-to-date database schema.

You must provide your configuration files and configuration arguments to this command, like you'd do with the
``harp-proxy server`` command, so that it points to the right storage.

.. code-block:: shell

    harp-proxy db:reset -f /path/to/config.yml

or...

.. code-block:: shell

    harp-proxy db:reset --set storage.url=...


Logging
:::::::

To instruct SQLAlchemy to log all queries, set ``LOGGING_SQL=INFO`` in your env.

.. code-block:: shell

    LOGGING_SQL=INFO harp-proxy server ...

It works with all HARP commands, not just ``server``.


Blob ids
::::::::

Blobs are content-addressed. A blob id is the SHA-256 of the content type (length-framed) and the body, truncated to
160 bits: 40 hexadecimal characters, so no schema change.

Blobs written by earlier versions carry SHA-1 ids. They keep resolving, and are not rewritten. A body already stored
under its old id is stored once more under its new id the next time it is seen, until retention removes the old row.

.. _upgrading-0-12:

Upgrading to 0.12
=================

What changes for an operator going from 0.11 to 0.12. The full list is in the
:doc:`changelog </changelogs/index>`; this page keeps what can change a running deployment.

Before you upgrade
::::::::::::::::::

**Back up the database first.** HARP 0.12 changes the storage schema, and there is no
documented way back to 0.11.

- **SQLite**: a file written by 0.11 is not migrated, and 0.12 refuses to start on it. Delete the file
  (it is recreated at next start) or run ``harp-proxy db:reset``. Its transactions are lost: export
  what you need before.
- **PostgreSQL and MySQL**: migrations run at boot by default, so starting 0.12 is enough. With
  ``storage.migrate: false``, run ``harp-proxy db:migrate up head`` **before** starting the new version.
  See :doc:`migrations` and :doc:`the storage page </apps/storage/index>`.
- **Drivers**: PostgreSQL and MySQL drivers are extras. Install ``harp-proxy[postgresql]`` or
  ``harp-proxy[mysql]``, or startup fails naming the extra. ``mysql+asyncmy://`` urls are refused: use
  ``mysql+aiomysql://``.
- **Applications list**: an ``applications:`` list in your configuration now replaces the default set
  (it used to be ignored). List every application you need, including dependencies such as ``proxy``
  for ``storage``, or remove the key.

Behaviour changes
:::::::::::::::::

Request and response bodies
---------------------------

- Response bodies are **streamed** to the client as they arrive. A transaction ends once the body is
  sent, so its duration and :doc:`TPDEX </user/performances>` now include the transfer to the client:
  expect longer figures for large bodies and slow clients.
- At most ``proxy.max_recorded_body_size`` (1 MiB) of a body is recorded, request or response. A longer
  one is forwarded whole but recorded truncated (``truncated-request-body``,
  ``truncated-response-body`` markers), and a truncated response is not stored in the HTTP cache.
  Raise the setting if you need more recorded.
- A client silent for longer than ``proxy.client_read_timeout`` (30 s) while sending a body, or sending
  below ``proxy.min_request_body_rate`` (1 KiB/s after 10 s), is answered ``408`` and its request is
  never forwarded upstream. Set ``min_request_body_rate`` to ``0`` to disable the rate check. See
  :ref:`proxy-buffering-and-streaming`.

Storage
-------

- SQLite enforces foreign keys: retention now also deletes the messages and tags of the transactions
  it removes, and the orphan sweep frees their blobs. A database that kept those rows will shrink.
- The dashboard transaction search matches substrings on every backend. On MySQL and MariaDB it used
  to match word prefixes, so it can return more transactions.
- File SQLite storage runs in WAL mode and adds ``-wal`` and ``-shm`` files next to the database:
  keep them together when copying or backing up.

Logging
-------

- Event dispatches are logged at ``debug`` instead of ``info``: log filters or alerts built on those
  lines stop matching.

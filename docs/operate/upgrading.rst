.. _upgrading-0-13:

Upgrading to 0.13
=================

Metrics
:::::::

- With the ``metrics`` application enabled, ``/.prometheus/metrics`` is no longer answered on the proxy
  ports: the request is proxied to the upstream like any other. Metrics are served on ``/metrics`` by the
  dashboard port, behind its authentication, and on ``dashboard.metrics_port`` when set. Point your scrape
  configuration at one of them. See :doc:`prometheus`.
- The ASGI-level metric families disappear with the middleware that produced them: ``requests_count``,
  ``requests_time``, ``requests_in_progress``, ``responses_count`` and ``exceptions_count``. Dashboards and
  alerts built on them stop matching: use the ``controller_*`` families instead (``controller_requests_count``,
  ``controller_requests_time``, ``controller_requests_in_progress``, ``controller_responses_count``,
  ``controller_exceptions_count``).
- Exception metrics lose their unbounded labels: ``path`` on ``controller_exceptions_count`` and ``url`` on
  ``remote_exceptions_count`` are removed (they grew the series count with every distinct path or query string).
  Aggregate queries still work; any ``by (path)`` or ``by (url)`` grouping, or matcher on these labels, stops
  matching. The remaining labels are listed in :doc:`prometheus`.

.. _upgrading-0-12:

Upgrading to 0.12
=================

What changes for an operator going from 0.11 to 0.12. The full list is in the
:doc:`changelog </changelogs/index>`; this page keeps what can change a running deployment.

Before you upgrade
::::::::::::::::::

**Back up the database first.** HARP 0.12 changes the storage schema. On PostgreSQL and MySQL, the way
back to 0.11 is :ref:`a down migration <upgrading-0-12-rollback>`.

- **SQLite**: a file written by 0.11 is not migrated, and 0.12 refuses to start on it. Delete the file
  (it is recreated at next start) or run ``harp-proxy db:reset``. Its transactions are lost: export
  what you need before.
- **PostgreSQL and MySQL**: migrations run at boot by default, so starting 0.12 is enough. With
  ``storage.migrate: false``, run ``harp-proxy db:migrate up heads`` **before** starting the new version.
  See :doc:`migrations` and :doc:`the storage page </apps/storage/index>`.
- **Drivers**: PostgreSQL and MySQL drivers are extras. Install ``harp-proxy[postgresql]`` or
  ``harp-proxy[mysql]``, or startup fails naming the extra. ``mysql+asyncmy://`` urls are refused: use
  ``mysql+aiomysql://``.
- **MySQL and MariaDB are deprecated**: they keep working and stay tested in CI, but have no production
  support and no performance commitment, and will be removed in a future version (not decided). HARP logs a
  warning at boot for them. PostgreSQL is the only production-supported database; SQLite is for development
  only. See :doc:`the storage page </apps/storage/index>`.
- **Applications list**: an ``applications:`` list in your configuration now replaces the default set
  (it used to be ignored). List every application you need, including dependencies such as ``proxy``
  for ``storage``, or remove the key.

.. _upgrading-0-12-rollback:

Rolling back to 0.11
::::::::::::::::::::

On PostgreSQL and MySQL, 0.12 records a new schema revision, ``c5e8b2d41f73``, which 0.11 does not know: a
0.11 started with ``storage.migrate: true`` fails at startup with ``Can't locate revision identified by
'c5e8b2d41f73'``. Before reinstalling 0.11, run this with 0.12:

.. code-block:: shell

    harp-proxy db:migrate down a1c7f3b52e04

It drops the ``transactions.markers`` column, so the markers of recorded transactions are lost, and nothing
else. ``a1c7f3b52e04`` is the revision 0.11 expects. See :doc:`migrations`.

SQLite never runs migrations, so there is nothing to undo there: restore your backup of the file.

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

Upstreams
---------

- Credentials in an endpoint url (``https://user:password@host/``) no longer appear in the ``Host``
  header. An ``Authorization`` header set by the client or a rule now takes precedence over them; 0.11
  replaced it with ``Authorization: Basic``. If you relied on url credentials overriding client
  authentication, check those endpoints.
- With the http cache, a successful (2xx or 3xx) ``POST``, ``PUT``, ``PATCH`` or ``DELETE`` invalidates
  the stored responses for its target and its same-host ``Location`` / ``Content-Location`` urls. Expect
  more requests to reach your upstreams after writes.
- The TLS trust store is certifi 2026.10.19 or later, which also drops roots Mozilla removed since
  2025.10 (DigiCert Global Root CA, DigiCert High Assurance EV, Entrust and AffirmTrust among them). An
  upstream whose chain ends only at one of them now fails TLS verification.

Storage
-------

- SQLite enforces foreign keys: retention now also deletes the messages and tags of the transactions
  it removes, and the orphan sweep frees their blobs. A database that kept those rows will shrink.
- The dashboard transaction search matches substrings on every backend. On MySQL and MariaDB it used
  to match word prefixes, so it can return more transactions.
- Load shedding engages only under sustained backlog: bodies, messages, then whole transactions stop
  being recorded once the storage queue has stayed at or above 100, 1,000 or 10,000 jobs for 2
  seconds, and recording resumes as soon as it drains. Short bursts are recorded in full. Above the
  :ref:`recording capacity <storage-recording-capacity>`, expect ``shed-bodies`` and
  ``shed-messages`` markers. ``async_worker_queue_backlog`` now reports 0, not 1, for an empty queue.
- File SQLite storage runs in WAL mode and adds ``-wal`` and ``-shm`` files next to the database:
  keep them together when copying or backing up.

Dashboard
---------

- **The dashboard now requires a login by default.** Without ``dashboard.auth``, HARP generates a random
  password for the ``admin`` user at each start and logs it once, in a ``Dashboard login`` line. It changes
  at every start and is nowhere else: not in the settings, the storage or any other log line.
- To pick your own users, configure ``dashboard.auth`` (``type: basic``): nothing is generated then, and
  nothing changes for deployments that already did.
- To keep the previous behaviour, set ``dashboard.auth.type: none`` (``--set dashboard.auth.type=none``).
  The dashboard is then open to anyone who can reach its port, and exposes the proxied traffic: HARP logs a
  warning at every start. Only do it behind a network boundary you trust.
- Scrapers, health checks or scripts calling the dashboard port (``/metrics``, ``/api/...``) must send the
  credentials, or use ``dashboard.metrics_port`` for Prometheus. See :doc:`/apps/dashboard/index`.

Known issue
-----------

- With the http cache stored in the same SQL database as the transactions (the default), a stalled
  database stalls proxied requests too: each cache read waits for the connection pool timeout (30 s),
  and some requests wait until the database is back. Recording sheds as documented, but traffic is
  slowed by the cache. If your database may stall and you can do without caching, disable the cache
  (``--disable http_cache``). Tracked in `#1352 <https://github.com/msqd/harp/issues/1352>`_. 0.11 behaves
  the same.

Logging
-------

- Event dispatches are logged at ``debug`` instead of ``info``: log filters or alerts built on those
  lines stop matching.

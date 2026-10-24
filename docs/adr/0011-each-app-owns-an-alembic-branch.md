# ADR-0011: Each application owns a branch of one alembic history

- **Status**: proposed
- **Date**: 2026-10-24
- **Decided in**: [explore/auth](https://github.com/msqd/harp/milestone/24)

**Proposed on the explore/auth exploration branch; nothing of it is implemented.** Line references are
to `main` when this record was written.

HARP keeps one alembic environment and one `alembic_version` table, and each application that owns
tables owns a branch of that history: its own `migrations/versions` folder and a `branch_label` named
after the application. `alembic_version` then holds one row per application head. An application's
tables carry its name as a prefix (`auth_accounts`, `audit_events`), and a migration that needs another
application's table says so with `depends_on`.

## The list of branches is static

`version_locations` lists every application under `harp_apps/` that has migrations, enabled or not, and
every branch is migrated on every database. A disabled application's tables exist and stay empty.

The list cannot follow the enabled applications. An application enabled once leaves its head in
`alembic_version`; disabled later, its folder would leave the list, and alembic would fail on a
revision it cannot locate. A static list closes that failure by construction.

## What changes

- Boot (`harp_apps/storage/__app__.py:36`), the test fixtures (`harp_apps/storage/conftest.py:74`) and
  the `db:*` commands upgrade to `heads` instead of `head`.
- `ensure_schema_is_current` checks every head.
- All models stay on storage's `Base`, because an in-memory SQLite database is built with
  `Base.metadata.create_all` (`harp_apps/storage/__app__.py:26`) and never sees alembic.
- Autogenerating a revision for one application filters the metadata with `include_object` on that
  application's table prefix (`<application>_`), so a revision never picks up another application's tables.
  Storage's tables predate the convention, so storage owns every table that no other application claims by prefix.
- A `naming_convention` on the metadata comes first, in the storage branch: today's constraints have no
  names, and SQLite batch migrations cannot alter an unnamed foreign key such as
  `trans_user_flags.user_id`.

## Rejected

- **One chain, in storage.** Nothing to change today, and branches can still start later without
  rewriting history. But every revision written meanwhile for auth, audit or the cache would stay in
  storage's folder for good, and an application could never be read with its own schema history.
- **One alembic environment per application.** Full independence, at the price of a version table per
  application, ordering code of our own between them, and cross-application foreign keys handled by
  hand.
- **A version table of our own, with an `application` column.** It duplicates what alembic branches
  already record, and needs the ordering code above.

Applications from outside `harp_apps/` that bring tables are out of scope; adding their folder to the
list is the expected path when one appears.

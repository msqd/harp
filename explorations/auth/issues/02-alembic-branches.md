# migrations: one alembic branch per application

**Problem**

Every table lives in storage's single alembic chain (`harp_apps/storage/migrations`). The auth, audit and cache-index tables coming from the explorations would all have to be written into storage's history. ADR-0012 (branch `explore/auth`) decides that each application owns a branch of one alembic history.

**Acceptance criteria**

- Storage's existing revisions form the `storage` branch (`branch_label`), with no revision rewritten: a database migrated from 0.12 upgrades without error.
- `version_locations` is a static list of every `harp_apps` application with a `migrations/versions` folder, enabled or not. Test: a database whose `alembic_version` holds the head of an application that is not enabled still boots.
- Boot (`harp_apps/storage/__app__.py`), test fixtures (`harp_apps/storage/conftest.py`) and `harp-proxy db:*` upgrade to `heads`; `ensure_schema_is_current` checks every head.
- `harp-proxy db:migrate` (status) shows the current revision per application.
- `harp-proxy db:create-migration` takes an application name and autogenerates only that application's tables (`include_object` on the table prefix). Test: a model change in one application does not appear in another's revision.
- Contributor docs describe how an application adds its branch.

**Out of scope**

Migrations shipped by applications outside `harp_apps/`.

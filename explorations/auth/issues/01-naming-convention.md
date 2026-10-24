# storage: name every constraint (naming_convention)

**Problem**

The storage metadata has no `naming_convention` (`harp_apps/storage/models/base.py`), so constraints carry database-generated names, or none on SQLite. Alembic batch migrations on SQLite cannot alter a constraint they cannot name, such as the foreign key `trans_user_flags.user_id → users.id`. Renaming `users` (explore/auth) and every later table change on SQLite depend on it.

**Acceptance criteria**

- `Base.metadata` carries a naming convention for indexes, unique, check, foreign and primary keys.
- A storage migration renames the existing constraints to the convention on PostgreSQL, MySQL and SQLite; downgrade restores the previous names. Test against each database (`@parametrize_with_database_urls`).
- `ensure_schema_is_current` passes on a database migrated from 0.12 and on one built with `create_all`.
- No functional change: every existing test passes unchanged.

**Out of scope**

Any table or column change.

# auth: take over `users` as `auth_accounts`, with roles enforced per route

**Problem**

`users(id, username varchar(32))` (`harp_apps/storage/models/users.py`) only serves favourites. There is no role: every authenticated request may do anything, and the system pages expose settings and dependency versions to anyone who gets in.

**Acceptance criteria**

- A new application `harp_apps/auth`, always loaded, owns the model and its alembic branch. Its first revision depends on the naming convention and renames `users` to `auth_accounts`: `username` widened to 255, plus `display_name`, `email` (nullable, unique, case-insensitive, stored lower-cased), `kind` (`person`, `machine`, `system`), `role` (`viewer`, `editor`, `admin`), `created_at`, `last_seen_at` (written at most once a minute), `disabled_at`. Existing rows become `person` / `admin`, `anonymous` becomes `system`. Favourites keep their author. Downgrade restores `users`. Tested on each database.
- Every dashboard route declares the role it requires: Viewer for overview, transactions, bodies, metrics; Editor for topology, storage state and `PUT /api/system/proxy`; Admin for settings and dependencies. A request below the role answers 403. Test per route.
- Resolving a request yields one actor context (account, effective role, `via`, `via_id`, optional client); controllers and role checks read only that, and `request.extensions["user"]` goes away. Effective role is `min(account role, credential cap)`, read from the account on every request; a disabled account answers 401.
- `harp auth:create-account <username> --role <role>` creates an account from the command line (password prompted or generated); it is also the access-recovery path.
- The frontend hides what the current role cannot use and shows the account and role in the header.

**Out of scope**

Sign-in methods (later children). Until password sign-in lands, Basic keeps working on this branch.

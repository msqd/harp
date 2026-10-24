# Auth data models in mature open-source software

Research input for the HARP `auth` app. Every claim points to the project's own source
(model, migration) or official documentation, pinned to the commit read on 2026-10-24.

Pinned revisions:

| Project | Repository | Commit |
|---|---|---|
| Sentry | getsentry/sentry | `86b1728a40fc` |
| GitLab | gitlabhq/gitlabhq | `d7b9a6176ab4` |
| Grafana | grafana/grafana | `ff4c677cdf3f` |
| Gitea | go-gitea/gitea | `8abda623122a` |
| Mattermost | mattermost/mattermost | `39637f182d9a` |
| Keycloak | keycloak/keycloak | `7e07aeecd728` |
| Django | django/django | `0e128d524d0a` |
| django-allauth | pennersr/django-allauth | `bd0ead7ac60d` |
| Ory Kratos | ory/kratos (+ ory/docs `4a8e1bb690e9`) | `b86338da04a0` |
| Supabase Auth (GoTrue) | supabase/auth (+ supabase/supabase `7e866ef83e89`) | `c3348e8f1cb3` |

## 1. Per-project findings

### 1.1 Sentry

- **Users.** Table `auth_user` (Django's legacy name kept), `username` unique, display name
  stored in a column still called `first_name` "for legacy reasons", `email` plus a
  separate nullable unique `email_unique`, booleans `is_staff`, `is_active`,
  `is_superuser`, `is_managed`, `is_sentry_app`, `is_suspended`, `last_password_change`,
  `session_nonce`, `date_joined`, `last_active`
  ([user.py#L105-L214](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L105-L214)).
  Email uniqueness is case-insensitive through an `Upper("email_unique")` index
  ([#L219](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L219)).
- **External identities.** `sentry_authidentity(user, auth_provider, ident, data, last_verified, last_synced, date_added)`,
  `unique_together = ((auth_provider, ident), (auth_provider, user))`: one subject per
  provider, and one identity per provider per user
  ([authidentity.py#L31-L91](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/authidentity.py#L31-L91)).
  Providers are rows in `sentry_authprovider(provider, config, default_role, ...)`
  ([authprovider.py#L38-L86](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/authprovider.py#L38-L86)).
- **Local password.** Inherited from Django `AbstractBaseUser.password` (see 1.7);
  `set_password` also stamps `last_password_change`
  ([user.py#L497-L500](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L497-L500)).
- **API tokens.** Prefixes are a typed enum: `sntryu_` (user), `sntrys_` (org), `sntrya_`
  (user app), `sntryi_` (integration); pre-prefix tokens remain valid
  ([types/token.py#L4-L16](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/types/token.py#L4-L16)).
  User token = prefix + `secrets.token_hex(32)`
  ([apitoken.py#L106-L110](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/apitoken.py#L106-L110)),
  stored as `hashed_token = sha256(token).hexdigest()` with a unique index, plus
  `token_last_characters` (4 chars) for display, `expires_at`, `scope_list`
  ([apitoken.py#L163](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/apitoken.py#L163),
  [#L200-L206](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/apitoken.py#L200-L206),
  [apiscopes.py#L87](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/apiscopes.py#L87)).
  The legacy plaintext `token` column still exists; authentication looks up by hash first,
  falls back to plaintext and backfills the hash
  ([authentication.py#L504-L548](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/api/authentication.py#L504-L548)):
  a migration cost HARP can avoid by hashing from day one.
  Org tokens embed a base64 JSON payload (`iat`, `url`, `org`) between prefix and secret:
  `sntrys_<payload>_<secret>`, parsed by requiring exactly two `_`
  ([orgauthtoken_token.py#L17-L41](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/utils/security/orgauthtoken_token.py#L17-L41)),
  hashed with plain SHA-256 ([#L57-L58](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/utils/security/orgauthtoken_token.py#L57-L58)).
  `sentry_orgauthtoken` has `token_hashed` unique, `token_last_characters`,
  `date_last_used`, `date_deactivated` (soft revoke)
  ([orgauthtoken.py#L58-L76](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/orgauthtoken.py#L58-L76)).
- **last_used throttling.** Org token `date_last_used` updated at most once a minute
  through a cache key ("Debounce updates, as we often get bursts of requests")
  ([orgauthtoken.py#L164-L184](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/models/orgauthtoken.py#L164-L184)).
  User `ApiToken` has no last-used column.
- **Service/bot accounts.** A flag on the user row: `is_sentry_app`, "Cannot login or use
  Sentry like a normal User would"
  ([user.py#L154-L163](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L154-L163)).
- **Roles.** Instance-level: booleans `is_staff`/`is_superuser` plus `sentry_userrole(name unique, permissions array)` and a join table `sentry_userrole_users`
  ([userrole.py#L20-L80](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/userrole.py#L20-L80)).
- **Sessions and revocation.** Django sessions, plus a per-user `session_nonce`
  (`CharField(12)`): `refresh_session_nonce` writes a new random value and copies it into
  the session ([user.py#L195](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L195),
  [#L502-L505](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L502-L505));
  the middleware treats a session whose `_nonce` differs as anonymous
  ([middleware/auth.py#L44-L50](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/middleware/auth.py#L44-L50)).
  This is the same idea as the draft's `session_epoch`.
- **Account linking.** Explicit. An unknown SSO identity is auto-linked only when the
  session user already owns the target account, or after a one-time email verification
  link; the code notes that IdP `email_verified` is not trusted
  ([auth/helper.py#L674-L737](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/auth/helper.py#L674-L737)).
- **Naming.** `sentry_` prefix on every table except the inherited `auth_user`.

### 1.2 GitLab

- **Users.** `users(id, email NOT NULL, encrypted_password NOT NULL DEFAULT '', username, name, admin boolean, state, user_type smallint DEFAULT 0, last_activity_on date, ...)`
  ([structure.sql#L699-L784](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L699-L780)).
  `user_type` is an enum: `human: 0`, `support_bot`, `alert_bot`, `ghost: 5`,
  `project_bot: 6`, `service_account: 13`, `placeholder`, `import_user`...
  ([has_user_type.rb#L7-L23](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/concerns/has_user_type.rb#L7-L23)).
- **External identities.** `identities(id, extern_uid, provider, user_id NOT NULL, created_at, updated_at, secondary_extern_uid, saml_provider_id, trusted_extern_uid)`
  ([structure.sql#L22703-L22714](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L22703-L22713)).
  The database has only non-unique indexes on `(provider, id)` and `user_id`
  ([#L49609-L49613](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L49609-L49613));
  uniqueness of `extern_uid` per provider (case-insensitive) and of one identity per
  provider per user is enforced in the model
  ([identity.rb#L10-L16](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/identity.rb#L10-L16)).
- **Local password.** On `users.encrypted_password`; bcrypt (`$2a$`) or
  PBKDF2-SHA512 (`$pbkdf2-sha512$`), detected by prefix, with transparent migration
  ([encrypted_user_password.rb#L3-L60](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/concerns/encrypted_user_password.rb#L3-L60)).
- **API tokens.** `personal_access_tokens(user_id, name, revoked boolean, expires_at date, scopes, impersonation, token_digest, last_used_at, previous_personal_access_token_id, description, user_type, ...)`
  with a unique index on `token_digest`
  ([structure.sql#L28308-L28334](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L28308-L28335),
  [#L51197](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L51197)).
  Prefix `glpat-`, configurable per instance
  ([personal_access_token.rb#L22-L31](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/personal_access_token.rb#L22-L31)).
  Digest = `SHA256.base64digest(token + db_key_base)`, i.e. a server-side pepper
  ([token_field/digest.rb#L30-L31](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/authn/token_field/digest.rb#L30-L31),
  [crypto_helper.rb#L11-L12](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/gitlab/crypto_helper.rb#L11-L12),
  [#L59-L60](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/gitlab/crypto_helper.rb#L59-L60));
  the pepper forces lookups over every key version after a rotation, plus a rewrite of
  stale digests ([digest.rb#L16-L21](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/authn/token_field/digest.rb#L16-L21),
  [#L56-L74](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/authn/token_field/digest.rb#L56-L74)).
  Lifetime capped at 365 days and an expiry is required by default
  ([personal_access_token.rb#L42-L43](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/personal_access_token.rb#L42-L43),
  [PAT docs#L224-L232](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/doc/user/profile/personal_access_tokens.md?plain=1#L224-L232)).
- **last_used throttling.** `LAST_USED_AT_TIMEOUT = 10.minutes`, update under an exclusive
  lease, with `update_columns` to avoid touching `updated_at`
  ([last_used_service.rb#L10-L36](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/services/personal_access_tokens/last_used_service.rb#L10-L36),
  [#L71-L72](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/services/personal_access_tokens/last_used_service.rb#L71-L72));
  documented as "updated every 10 minutes"
  ([PAT docs#L161](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/doc/user/profile/personal_access_tokens.md?plain=1#L161)).
- **Service accounts.** Rows in `users` with a non-human `user_type` (above).
- **Roles.** Instance admin is a column (`users.admin`, [#L714](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/db/structure.sql#L714)); token rights are `scopes`.
- **Sessions.** Server-side in Redis, with a per-user lookup so all sessions of a user can
  be listed and destroyed ([active_session.rb#L6-L12](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/active_session.rb#L6-L12),
  [#L74-L75](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/active_session.rb#L74-L75),
  [#L129](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/app/models/active_session.rb#L129)).
- **Account linking.** `auto_link_user` links on email match, off by default; the default
  is a guided flow that requires signing in, documented as "more secure than
  `auto_link_user`, which links accounts on email match alone"
  ([omniauth.md#L56](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/doc/integration/omniauth.md?plain=1#L56),
  [#L289-L306](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/doc/integration/omniauth.md?plain=1#L289-L306),
  [o_auth/user.rb#L86](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/gitlab/auth/o_auth/user.rb#L86),
  [#L318-L324](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/lib/gitlab/auth/o_auth/user.rb#L318-L324)).
- **Naming.** No prefix; plural snake_case.

### 1.3 Grafana

- **Users.** Table `user` (a reserved word, quoted in raw SQL), `login` and `email` unique,
  `name`, `password`, `salt`, `rands`, `is_admin` (server admin), `email_verified`,
  later `last_seen_at`, `is_disabled`, `is_service_account`
  ([user_mig.go#L54-L143](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/user_mig.go#L54-L143)).
- **Local password.** `PBKDF2(SHA-256, password, salt, 10000, 50)` hex, with a separate
  `salt` column ([encoding.go#L52-L58](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/util/encoding.go#L52-L58)).
  The algorithm is not recorded per row.
- **External identities.** `user_auth(user_id, auth_module, auth_id, created, o_auth_* tokens, external_uid, user_uid)`;
  the index on `(auth_module, auth_id)` is **not unique**
  ([user_auth_mig.go#L7-L58](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/user_auth_mig.go#L7-L58)),
  and the codebase ships clean-up queries for duplicate rows
  ([lookup_duplicate_user_auth.sql](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/login/authinfoimpl/queries/lookup_duplicate_user_auth.sql),
  [delete_duplicate_user_auth.sql](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/login/authinfoimpl/queries/delete_duplicate_user_auth.sql)).
- **API tokens / service accounts.** `api_key(org_id, name, key unique, role, created, updated, expires bigint, service_account_id, last_used_at, is_revoked)`
  ([apikey_mig.go#L42-L105](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/apikey_mig.go#L42-L105)).
  Format `gl<serviceID>_<secret>_<crc32>`; service account tokens are `glsa_...`; the
  CRC32 checksum lets the server reject a malformed token before any DB access, and parsing
  splits on `_` expecting exactly three parts
  ([tokengen.go#L12-L96](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/components/satokengen/tokengen.go#L12-L96)).
  The stored value is PBKDF2 of the secret salted with the checksum, so it is
  deterministic and looked up directly by hash
  ([tokengen.go#L27-L33](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/components/satokengen/tokengen.go#L27-L33),
  [api_key.go#L112-L122](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/authn/clients/api_key.go#L112-L122)).
  Expiry, revocation and "must belong to a service account" checks:
  [api_key.go#L224-L237](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/authn/clients/api_key.go#L224-L237).
  Service accounts are `user` rows with `is_service_account`; their role comes from
  `org_user.role`, not from the token
  ([user_mig.go#L134-L143](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/user_mig.go#L134-L143),
  [api_key.go#L244-L246](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/authn/clients/api_key.go#L244-L246)).
- **last_used throttling.** Only when `last_used_at` is null or older than 5 minutes
  ([api_key.go#L254-L255](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/authn/clients/api_key.go#L254-L255)).
- **Roles.** A column: `org_user.role` varchar(20) (Viewer/Editor/Admin), plus `user.is_admin`
  ([org_mig.go#L32-L37](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/org_mig.go#L32-L37)).
- **Sessions.** Server-side `user_auth_token(user_id, auth_token unique, prev_auth_token unique, user_agent, client_ip, auth_token_seen, seen_at, rotated_at, created_at, updated_at, revoked_at)`
  ([user_auth_token_mig.go#L11-L49](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/user_auth_token_mig.go#L11-L49)).
  The cookie token is stored as `sha256(token + secret_key)`
  ([auth_token.go#L915-L918](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/auth/authimpl/auth_token.go#L915-L918)),
  rotated periodically (`prev_auth_token` absorbs races), and revocable per token or per
  user ([#L344](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/auth/authimpl/auth_token.go#L344),
  [#L508](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/auth/authimpl/auth_token.go#L508),
  [#L573](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/auth/authimpl/auth_token.go#L573)).
- **Account linking.** By IdP unique ID; email lookup sits behind
  `oauth_allow_insecure_email_lookup = false`, and the docs "strongly recommend against"
  enabling it ([configure-authentication#L157-L172](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/docs/sources/setup-grafana/configure-access/configure-authentication/_index.md?plain=1#L157-L172)).
- **Table changes.** Grafana reshapes tables by creating `x_v2`, copying the data, and
  dropping `x_v1` ([apikey_mig.go#L58-L76](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/apikey_mig.go#L58-L76)).

### 1.4 Gitea

- **Users.** One `user` table for people, organisations, bots and reserved names,
  discriminated by `type` (`UserTypeIndividual = 0`, `Organization`, `UserReserved`,
  `OrganizationReserved`, `Bot = 4`, `RemoteUser`)
  ([user.go#L52-L68](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/user/user.go#L52-L68)).
  Columns include `lower_name` and `name` unique, `email`, `passwd`, `passwd_hash_algo`
  (default `argon2`), `salt`, `login_source`, `last_login_unix`, `is_active`, `is_admin`,
  `is_restricted`, `prohibit_login`
  ([user.go#L96-L145](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/user/user.go#L96-L145)).
- **System users** (ghost, Actions, deploy key, CLI) are virtual objects with negative IDs
  (`-1` to `-5`), never stored
  ([user_system.go#L14](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/user/user_system.go#L14),
  [#L50-L53](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/user/user_system.go#L50-L53)).
- **Local password.** Algorithm recorded per row in `passwd_hash_algo`; configured defaults
  are parameter strings such as `argon2$2$65536$8$50`, `pbkdf2$50000$50`
  ([hash/setting.go#L13-L30](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/modules/auth/password/hash/setting.go#L13-L30)).
- **External identities.** `external_login_user` primary key `(external_id, login_source_id)`,
  `user_id` indexed, `provider`, `raw_data` JSON, stored OAuth tokens
  ([external_login_user.go#L48-L63](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/user/external_login_user.go#L48-L63)).
- **API tokens.** `access_token(uid, name, token_hash unique, token_salt, token_last_eight indexed, scope, created_unix, updated_unix)`;
  token = 20 random bytes hex; hash = `PBKDF2(token, per-token salt, 10000, 50, SHA-256)`
  ([access_token.go#L20-L53](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/auth/access_token.go#L20-L53),
  [twofactor.go#L79-L82](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/auth/twofactor.go#L79-L82)).
  Because the salt is per token, lookup selects candidates by `token_last_eight`, hashes
  each, compares in constant time, and caches the hit in an LRU
  ([access_token.go#L88-L127](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/auth/access_token.go#L88-L127)).
  No expiry or revoked column: revocation is deletion; "last used" is `updated_unix`
  ([#L36-L39](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/auth/access_token.go#L36-L39)).
- **Roles.** Columns `is_admin`, `is_restricted`.
- **Sessions.** Server-side table `session(key CHAR(16) pk, data BLOB, expiry)`
  ([session.go#L16-L18](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/models/auth/session.go#L16-L18)).
- **Account linking.** `[oauth2_client] ACCOUNT_LINKING = login` by default (show a
  login-to-link page); `auto` links directly
  ([app.example.ini#L1805-L1812](https://github.com/go-gitea/gitea/blob/8abda623122ae187df3d8ed339cfd656a86c29be/custom/conf/app.example.ini#L1805-L1812)).

### 1.5 Mattermost

- **Users.** `Users(Id, Username unique, Password, AuthData unique, AuthService, Email unique, EmailVerified, Roles, IsBot, LastActivityAt, LastLogin, DeleteAt, ...)`
  ([model/user.go#L94-L128](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/public/model/user.go#L94-L128),
  [000046_create_users.up.sql#L6-L15](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/db/migrations/postgres/000046_create_users.up.sql#L6-L15)).
  A user has **one** login method: `AuthService` + `AuthData` live on the user row, not in
  an identity table; `AuthData` is globally unique, not per service.
- **Local password.** PHC strings; current hasher is PBKDF2-SHA256, work factor 600000
  (`$pbkdf2$f=SHA256,w=600000,l=32$...`); legacy bcrypt still verified; `IsPHCValid`
  detects parameter drift to trigger re-hash
  ([hashers.go#L10-L29](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/app/password/hashers/hashers.go#L10-L29),
  [#L51-L85](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/app/password/hashers/hashers.go#L51-L85),
  [pbkdf2.go#L28-L36](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/app/password/hashers/pbkdf2.go#L28-L36),
  [#L92](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/app/password/hashers/pbkdf2.go#L92)).
- **API tokens.** `UserAccessTokens(Id, Token VARCHAR(26) UNIQUE, UserId, Description, IsActive)`,
  later `ExpiresAt` (migration 187) and `LastNotifiedAt`
  ([000030_create_user_access_tokens.up.sql#L1-L8](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/db/migrations/postgres/000030_create_user_access_tokens.up.sql#L1-L8),
  [user_access_token.go#L18-L36](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/public/model/user_access_token.go#L18-L36)).
  Stored and looked up **in plaintext** (`WHERE Token = ?`)
  ([user_access_token_store.go#L169-L172](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/store/sqlstore/user_access_token_store.go#L169-L172));
  revocation sets `IsActive` false and deletes the sessions minted from the token
  ([#L88-L99](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/store/sqlstore/user_access_token_store.go#L88-L99)).
- **Bots.** `Users.IsBot` on the user row ([user.go#L121](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/public/model/user.go#L121)).
- **Roles.** A space-separated string column `Users.Roles`, copied onto each session.
- **Sessions.** Server-side `Sessions(Id, Token, CreateAt, ExpiresAt, LastActivityAt, UserId, DeviceId, Roles, IsOAuth, Props)`
  ([000022_create_sessions.up.sql#L1-L20](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/channels/db/migrations/postgres/000022_create_sessions.up.sql#L1-L20),
  [session.go#L69-L82](https://github.com/mattermost/mattermost/blob/39637f182d9a541d92a0841117e9c1da6d008c4c/server/public/model/session.go#L69-L82)).
- **Naming.** PascalCase, no prefix.

### 1.6 Keycloak

- **Users.** `USER_ENTITY(ID varchar(36), USERNAME, EMAIL, EMAIL_CONSTRAINT, EMAIL_VERIFIED, ENABLED, REALM_ID, FEDERATION_LINK, SERVICE_ACCOUNT_CLIENT_LINK, NOT_BEFORE, CREATED_TIMESTAMP, ...)`,
  unique `(REALM_ID, USERNAME)` and `(REALM_ID, EMAIL_CONSTRAINT)`
  ([UserEntity.java#L61-L128](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/entities/UserEntity.java#L61-L128)).
  `EMAIL_CONSTRAINT` defaults to a random ID and holds the email only when the realm
  requires unique emails: a trick to switch uniqueness on and off without DDL
  ([#L90-L93](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/entities/UserEntity.java#L90-L93)).
- **Credentials apart from the user.** `CREDENTIAL(ID, TYPE, USER_LABEL, CREATED_DATE, USER_ID, SECRET_DATA, CREDENTIAL_DATA, PRIORITY, ...)`:
  passwords, OTP and WebAuthn are rows of one table, the hash in `SECRET_DATA` and the
  algorithm and iterations in `CREDENTIAL_DATA`
  ([CredentialEntity.java#L43-L78](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/entities/CredentialEntity.java#L43-L78),
  [PasswordCredentialData.java](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/server-spi/src/main/java/org/keycloak/models/credential/dto/PasswordCredentialData.java)).
  Default hash: Argon2 (non-FIPS), PBKDF2-SHA512 (FIPS)
  ([password-policies.adoc#L37-L47](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/docs/documentation/server_admin/topics/authentication/password-policies.adoc?plain=1#L37-L47)).
- **External identities.** `FEDERATED_IDENTITY(USER_ID, IDENTITY_PROVIDER, REALM_ID, FEDERATED_USER_ID, FEDERATED_USERNAME, TOKEN)`,
  primary key `(IDENTITY_PROVIDER, USER_ID)`; login looks up by
  `(realm, provider, federated user id)`
  ([FederatedIdentityEntity.java#L38-L67](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/entities/FederatedIdentityEntity.java#L38-L67)).
- **Service accounts.** A `USER_ENTITY` row linked to an OAuth client via
  `SERVICE_ACCOUNT_CLIENT_LINK`.
- **Roles.** Tables: `USER_ROLE_MAPPING(USER_ID, ROLE_ID)`
  ([UserRoleMappingEntity.java#L48-L59](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/entities/UserRoleMappingEntity.java#L48-L59)).
- **Sessions and revocation.** In-memory (Infinispan) user sessions with a persisted
  `OFFLINE_USER_SESSION` table
  ([PersistentUserSessionEntity.java#L125](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/model/jpa/src/main/java/org/keycloak/models/jpa/session/PersistentUserSessionEntity.java#L125)).
  `NOT_BEFORE` on the user (and on realm and client) invalidates every token issued before
  that time ([revocation.adoc#L16](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/docs/documentation/server_admin/topics/sessions/revocation.adoc?plain=1#L16)):
  the closest cousin of the draft `session_epoch`.
- **Account linking.** The default first-broker-login flow asks the user to confirm and
  prove ownership (re-authenticate or verify by email); "Automatically linking the existing
  local account to the external identity provider is a potential security hole"
  ([first-login-flow.adoc#L9](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/docs/documentation/server_admin/topics/identity-broker/first-login-flow.adoc?plain=1#L9),
  [#L40-L48](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/docs/documentation/server_admin/topics/identity-broker/first-login-flow.adoc?plain=1#L40-L48)).
  Auto-link without prompt requires building a custom flow
  ([#L55-L72](https://github.com/keycloak/keycloak/blob/7e07aeecd7281e6cd90a0dcc46957d74332dd553/docs/documentation/server_admin/topics/identity-broker/first-login-flow.adoc?plain=1#L55-L72)).
- **Naming.** Uppercase, no prefix.

### 1.7 Django `contrib.auth` and django-allauth

- **Users.** `auth_user`: `password varchar(128)`, `last_login`, `is_superuser`,
  `username`, `first_name`, `last_name`, `email` (not unique), `is_staff`, `is_active`,
  `date_joined` ([base_user.py#L44-L45](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/base_user.py#L44-L45),
  [models.py#L322-L531](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/models.py#L322-L531)).
  Roles are tables: `auth_group`, `auth_permission` and M2M joins.
- **Password format.** `<algorithm>$<iterations>$<salt>$<hash>`; default
  `pbkdf2_sha256` at 1,800,000 iterations, Argon2 available; `must_update` triggers a
  re-hash when parameters change; an unusable password starts with `!`
  ([hashers.py#L25](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/hashers.py#L25),
  [#L316-L326](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/hashers.py#L316-L326),
  [#L361-L364](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/hashers.py#L361-L364),
  [global_settings.py#L550-L553](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/conf/global_settings.py#L550-L553)).
- **Sessions.** Server-side by default (`SESSION_ENGINE = ...backends.db`, table
  `django_session(session_key, session_data, expire_date)`)
  ([global_settings.py#L510](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/conf/global_settings.py#L510),
  [base_session.py#L28-L30](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/sessions/base_session.py#L28-L30)).
  Each session also stores an HMAC of the password field; when the password changes the
  hash no longer matches and the session is dropped
  ([base_user.py#L132-L149](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/base_user.py#L132-L149),
  [auth/\_\_init\_\_.py#L175-L195](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/django/contrib/auth/__init__.py#L175-L195)).
  This is an implicit epoch tied to the password only.
- **allauth identities.** `socialaccount_socialaccount(user, provider, uid, last_login, date_joined, extra_data)`,
  `unique_together = ("provider", "uid")`; `uid` length is bounded because MySQL cannot
  index long unique strings (comment in the model)
  ([socialaccount/models.py#L91-L123](https://github.com/pennersr/django-allauth/blob/bd0ead7ac60dd722d62789653472de1521fc7fba/allauth/socialaccount/models.py#L91-L123)).
  Per-device sessions for listing and revoking: `usersessions_usersession(user, created_at, ip, last_seen_at, session_key, user_agent, data)`
  ([usersessions/models.py#L88-L99](https://github.com/pennersr/django-allauth/blob/bd0ead7ac60dd722d62789653472de1521fc7fba/allauth/usersessions/models.py#L88-L99)).
- **allauth linking.** `SOCIALACCOUNT_EMAIL_AUTHENTICATION` defaults to `False`, because
  "an untrustworthy provider can login to any local account by fabricating social account
  data"; it can be enabled per provider; auto-connect is a second opt-in
  ([configuration.rst#L16-L39](https://github.com/pennersr/django-allauth/blob/bd0ead7ac60dd722d62789653472de1521fc7fba/docs/socialaccount/configuration.rst?plain=1#L16-L39)).
- **Naming.** `<app_label>_<model>`: hence `auth_user`, `auth_group`. HARP's planned
  `auth_` prefix follows the same convention.
- **Changing the user table later.** The Django docs call changing `AUTH_USER_MODEL`
  mid-project "complex": it "can't be done automatically and requires manually fixing
  your schema, moving your data from the old user table"
  ([customizing.txt#L436-L446](https://github.com/django/django/blob/0e128d524d0a7c55a955570d6e5da983ac6ce6c7/docs/topics/auth/customizing.txt?plain=1#L436-L446)).

### 1.8 Ory Kratos

- **Identities and credentials.** `identities(id, schema_id, state, traits JSON, metadata_public, metadata_admin, organization_id, nid, ...)`
  ([identity.go#L90-L194](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/identity/identity.go#L90-L194)).
  Credentials are separate: `identity_credentials(id, identity_id, identity_credential_type_id, config JSON, version, ...)`,
  type lookup in `identity_credential_types(name)`, and the login keys in
  `identity_credential_identifiers(identifier, identity_id, identity_credential_id, identity_credential_type_id, nid)`
  ([credentials.go#L175-L263](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/identity/credentials.go#L175-L263)),
  unique `(nid, identity_credential_type_id, identifier)`
  ([unique_credentials.postgres.up.sql](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/persistence/sql/migrations/sql/20210817181232000005_unique_credentials.postgres.up.sql#L1)).
- **OIDC identifier format** is exactly `"<provider>:<subject>"`
  ([credentials_oidc.go#L111-L113](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/identity/credentials_oidc.go#L111-L113)),
  matching the draft's `oidc:<name>` plus `subject`.
- **Password** lives in the password credential's `config.hashed_password`
  ([credentials_password.go#L10-L11](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/identity/credentials_password.go#L10-L11)):
  the same "password on the identity, not on the user" shape as the draft.
- **Sessions.** Server-side `sessions(identity_id, token, logout_token, active, expires_at, authenticated_at, issued_at, ...)`
  ([session.go#L69-L169](https://github.com/ory/kratos/blob/b86338da04a040247a07f46100a86dcfb3875909/session/session.go#L69-L169)).
- **Linking.** Default strategy `confirm_with_existing_credential`; automatic linking only
  for imported users and for Google/Apple consumer accounts with verified email on both
  sides; the docs warn that providers set `email_verified` inconsistently
  ([account-linking.mdx#L10-L15](https://github.com/ory/docs/blob/4a8e1bb690e9538235095595eabd3fa72a82d571/docs/kratos/social-signin/95_account-linking.mdx?plain=1#L10-L15),
  [#L232-L241](https://github.com/ory/docs/blob/4a8e1bb690e9538235095595eabd3fa72a82d571/docs/kratos/social-signin/95_account-linking.mdx?plain=1#L232-L241),
  [#L254-L294](https://github.com/ory/docs/blob/4a8e1bb690e9538235095595eabd3fa72a82d571/docs/kratos/social-signin/95_account-linking.mdx?plain=1#L254-L294)).

### 1.9 Supabase Auth (GoTrue)

- **Users.** `auth.users(id uuid, aud, role, email, is_sso_user, encrypted_password, email_confirmed_at, last_sign_in_at, banned_until, deleted_at, is_anonymous, ...)`
  ([user.go#L26-L74](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/internal/models/user.go#L26-L74)).
  Password is bcrypt by default; Argon2 and Firebase scrypt hashes are accepted for import
  ([crypto/password.go#L36-L60](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/internal/crypto/password.go#L36-L60),
  [#L373-L383](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/internal/crypto/password.go#L373-L383)).
- **Identities.** `auth.identities(id uuid pk, provider_id, user_id, identity_data JSON, provider, last_sign_in_at, email generated, ...)`,
  unique `(provider_id, provider)`
  ([identity.go#L17-L32](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/internal/models/identity.go#L17-L32),
  [20231117164230_add_id_pkey_identities.up.sql#L5-L27](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/migrations/20231117164230_add_id_pkey_identities.up.sql#L5-L27)).
  Password users also get an identity row with `provider = 'email'`, backfilled for
  existing users by migration, so "every login method is an identity" holds even though
  the hash stays on `users`
  ([20221125140132_backfill_email_identity.up.sql#L1-L9](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/migrations/20221125140132_backfill_email_identity.up.sql#L1-L9)).
  The same migration also shows the history: the column was first called `id` and was
  renamed `provider_id` when a surrogate key was added.
- **Sessions.** Server-side `auth.sessions(id, user_id, not_after, aal, refreshed_at, user_agent, ip, ...)`
  with refresh tokens; short-lived JWT access tokens
  ([sessions.go#L79-L106](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/internal/models/sessions.go#L79-L106)).
- **Linking.** The divergent case: Supabase **automatically links** identities that share
  an email, and removes unconfirmed identities on the target user to block pre-account
  takeover; SAML SSO users are excluded
  ([auth-identity-linking.mdx#L17-L25](https://github.com/supabase/supabase/blob/7e866ef83e89e35cdda45a6c98abd069d5fa1b2f/apps/docs/content/guides/auth/auth-identity-linking.mdx?plain=1#L17-L25)).
- **Naming.** A dedicated `auth` schema rather than a table prefix.

### 1.10 Token prefixes elsewhere

GitHub documents typed prefixes `ghp_`, `github_pat_`, `gho_`, `ghs_`... "to indicate
the token's type" ([GitHub docs, token formats](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github#githubs-token-formats)).

## 2. Comparison table

| | Users table | External identity | Unique (provider, subject) in DB | Password location / format | Token storage | Token prefix | last_used throttle | Service accounts | Roles | Sessions | Auto-link by email |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Sentry | `auth_user` | `sentry_authidentity` | yes, + (provider, user) | user row, Django format | SHA-256 hex, unique | `sntryu_`, `sntrys_` | 1 min (org tokens) | flag `is_sentry_app` | bools + role tables | Django + `session_nonce` | no (verify) |
| GitLab | `users` | `identities` | no (model only) | user row, bcrypt / PBKDF2 prefix | SHA-256 + pepper, unique | `glpat-` | 10 min + lease | `user_type` enum | `admin` bool + scopes | Redis | opt-in |
| Grafana | `user` | `user_auth` | **no**, dedup queries | user row, PBKDF2 + salt column | PBKDF2 deterministic | `glsa_` + CRC32 | 5 min | flag `is_service_account` | column `org_user.role` | table, hashed, rotated | opt-in, "insecure" |
| Gitea | `user` | `external_login_user` | yes (PK) | user row + `passwd_hash_algo` | PBKDF2 salted, lookup by last 8 | none | none (`updated_unix`) | `type = Bot`; virtual system users | bools | table | `login` default |
| Mattermost | `Users` | on user row | `AuthData` unique | user row, PHC | **plaintext** | none | n/a | flag `IsBot` | string column | table | n/a |
| Keycloak | `USER_ENTITY` | `FEDERATED_IDENTITY` | PK (provider, user) | `CREDENTIAL` table, Argon2 | n/a (OAuth) | n/a | n/a | user + client link | role tables | Infinispan + `NOT_BEFORE` | no (custom flow) |
| Django + allauth | `auth_user` | `socialaccount_socialaccount` | yes | user row, `algo$iter$salt$hash` | n/a | n/a | n/a | n/a | group tables | DB + password HMAC | opt-in, per provider |
| Kratos | `identities` | `identity_credential_identifiers` | yes (type, identifier) | credential `config` | n/a | n/a | n/a | n/a | n/a | table | no (confirm) |
| GoTrue | `auth.users` | `auth.identities` | yes | user row, bcrypt | n/a | n/a | n/a | n/a | `role` column | table + JWT | **yes** |

## 3. Where projects converge

1. **One users table for every kind of principal.** Bots and service accounts are users
   with a discriminator: an enum (GitLab `user_type`, Gitea `type`) or a flag (Grafana
   `is_service_account`, Mattermost `IsBot`, Sentry `is_sentry_app`, Keycloak
   `SERVICE_ACCOUNT_CLIENT_LINK`). Tokens always belong to a user.
2. **Identities keyed by (provider, subject), enforced unique.** Sentry, Gitea, allauth,
   Kratos and GoTrue enforce it in the database. Grafana did not, and now carries
   duplicate-detection and clean-up queries; GitLab relies on model validation.
3. **Self-describing password hashes** with re-hash on login when parameters drift: Django
   format, Mattermost PHC, GitLab prefix detection, Gitea `passwd_hash_algo`, Keycloak
   `CREDENTIAL_DATA`. Current defaults: Argon2 (Keycloak, Gitea) or PBKDF2-SHA256 with
   600k+ iterations (Mattermost 600k, Django 1.8M).
4. **Typed, greppable token prefixes** (`sntryu_`, `glpat-`, `glsa_`, `ghp_`), the token
   shown once, only a digest stored, a short tail kept for display (Sentry
   `token_last_characters`, Gitea `token_last_eight`).
5. **Fast digest, unique index, O(1) lookup** for high-entropy tokens: Sentry and GitLab
   use SHA-256 (GitLab adds a server pepper). Gitea's per-token salt forces a candidate
   lookup by suffix; Grafana gets determinism by salting with the checksum.
6. **Expiry and soft revocation as columns**: GitLab `expires_at` + `revoked`, Grafana
   `expires` + `is_revoked`, Mattermost `ExpiresAt` (added late) + `IsActive`, Sentry org
   `date_deactivated`. GitLab requires an expiry by default (365 days).
7. **Throttled last-used writes**: 1 min (Sentry), 5 min (Grafana), 10 min (GitLab).
8. **Server-side sessions** so a session can be listed and revoked (Grafana, Mattermost,
   Gitea, Django, Kratos, GoTrue, GitLab Redis). Where sessions are not a row, a per-user
   invalidation stamp does the job: Sentry `session_nonce`, Keycloak `NOT_BEFORE`, Django
   password HMAC.
9. **No silent linking by email by default** (Sentry, GitLab, Grafana, Gitea, Keycloak,
   allauth, Kratos). Projects that allow it make it an explicit opt-in, often per
   provider, and require a verified email.

## 4. Divergences and why

- **Password on the user vs on a credential.** Most store the hash on the user row.
  Keycloak (`CREDENTIAL`) and Kratos (`identity_credentials`) separate it because they
  support several credential types per user (OTP, WebAuthn, passkeys); GoTrue keeps the
  hash on the user but still writes an `email` identity row so every login method is listed.
- **Roles as a column vs tables.** Products with a fixed small set of roles use a column
  (Grafana `org_user.role`, Mattermost `Roles`, GoTrue `role`, GitLab `admin`). Identity
  platforms and frameworks with custom roles use tables (Keycloak, Django groups, Sentry
  `UserRole`).
- **Token hashing.** Plaintext (Mattermost, Sentry's legacy column) is the outlier and
  Sentry is paying to migrate away. Pepper vs no pepper: GitLab's pepper protects a leaked
  database dump, but costs multi-key lookups after rotation.
- **Account linking.** GoTrue auto-links on email for consumer-app convenience and
  compensates by deleting unconfirmed identities; everyone else treats IdP email claims as
  untrusted.
- **Single identity per user** (Mattermost `AuthService`/`AuthData`) vs many (everyone
  else). The single-identity model makes switching from password to SSO a migration of the
  user row.

## 5. Implications for the HARP draft

### 5.1 `auth_users`

- `kind human|service|system` matches the convergent pattern (GitLab, Gitea). HARP's
  existing `"anonymous"` fallback row used by `UsersRepository.find_one_by_username`
  (`harp_apps/storage/models/users.py`) is a `system` user; Gitea instead keeps system
  users virtual with negative IDs. Keeping it as a stored `kind=system` row is simpler,
  because `trans_user_flags.user_id` needs a real foreign-key target.
- `role viewer|operator|admin` as a column with a CHECK constraint fits a fixed hierarchy
  (Grafana's model). Tables are only worth it once roles become user-defined.
- `email`: nullable (service and system users have none), unique, case-insensitive (Sentry's
  `Upper(email_unique)` index). Do not use it as a linking key (5.3).
- `session_epoch`: same mechanism as Sentry `session_nonce` and Keycloak `NOT_BEFORE`. Bump
  it on password change (Django does this implicitly), disable, role downgrade, and
  "log out everywhere". An integer counter is enough for signed cookies; a timestamp
  (Keycloak) also answers "revoke what was issued before T". A signed cookie plus epoch
  cannot list or revoke one device; every surveyed product with a session UI uses a table
  (Grafana `user_auth_token`, allauth `usersessions`). Accept that limit knowingly or plan a
  `auth_sessions` table.
- `last_seen_at`: throttle the write the same way as for tokens (Grafana has `last_seen_at`
  on `user`).
- `disabled_at`: equivalent to Grafana `is_disabled`, Sentry `is_suspended`, GoTrue
  `banned_until`; a timestamp is strictly more informative than a boolean.

### 5.2 `auth_identities`

- `unique(provider, subject)` in the database: do it; Grafana's duplicate clean-up
  queries show the cost of not doing it. Also consider `unique(user_id, provider)` (Sentry,
  Keycloak's PK) unless a user may hold two accounts at the same IdP.
- `provider 'local' | 'oidc:<name>'` mirrors Kratos (`provider:subject` identifiers) and
  GoTrue (`email` provider row for password users). For `local`, the subject should be the
  normalised (lowercased) username, updated when the username changes.
- `password_hash` nullable PHC on the identity matches Kratos and Keycloak. Store full PHC
  strings, re-hash on successful login when parameters differ (Django `must_update`,
  Mattermost `IsPHCValid`). Argon2id or PBKDF2-SHA256 ≥ 600k are the sourced defaults.
- Size `subject` for MySQL unique-index limits (allauth bounds `uid` for this reason) and
  compare it exactly; GitLab normalises LDAP DNs only, never OIDC `sub`.
- `last_login_at` on the identity matches allauth `SocialAccount.last_login`, GoTrue
  `identities.last_sign_in_at`, Sentry `last_verified`.

### 5.3 Linking

Default to explicit linking: an admin creates the user and its identity, or a signed-in
user links a provider. Offer email-based linking only as a per-provider opt-in that
requires `email_verified` (allauth, GitLab, Grafana, Kratos all do this), and never by
default (GoTrue is the only surveyed default-on, with compensating clean-up).

### 5.4 `auth_tokens`

- Format `harp_<prefix>_<secret>` follows the industry (typed prefix, greppable). Parsers
  split on `_` (Grafana requires exactly three parts, Sentry counts two `_`), so generate
  `prefix` and `secret` from an alphabet without `_` (hex or base62, not base64url).
  Consider a short checksum suffix as Grafana does (CRC32) to reject typos and enable
  offline detection by secret scanners.
- `prefix` unique + `secret_hash = sha256(secret)` gives an indexed lookup followed by a
  constant-time compare, equivalent to Sentry and GitLab. Hash the full token or the secret,
  but never store plaintext (Sentry's dual-column migration is the cautionary tale). A
  server-side pepper (GitLab) is optional; it adds key-rotation work.
- `role` nullable "capped by owner": compute the effective role at request time as
  `min(token.role or owner.role, owner.role)`, so demoting or disabling the owner
  immediately caps every token. This mirrors Grafana service-account tokens taking their
  role from the account, and GitLab scopes acting within the user's own permissions.
- `expires_at`: make it present from day one (Mattermost added it as migration 187),
  and consider a default lifetime (GitLab: 365 days, required by default).
- `revoked_at` timestamp instead of delete keeps an audit trail (GitLab, Grafana, Sentry
  org tokens); Gitea deletes.
- `last_used_at`: update only when older than a few minutes (1, 5 and 10 minutes in
  Sentry, Grafana, GitLab). A conditional
  `UPDATE ... WHERE id = :id AND (last_used_at IS NULL OR last_used_at < :threshold)`
  avoids GitLab's lease without extra infrastructure.
- Tokens for `kind=service` users are the service-account pattern (Grafana `glsa_`, GitLab
  `service_account` users with PATs).

### 5.5 Table naming

`auth_` prefix matches Django's `<app_label>_<model>` convention (`auth_user`). Plural
names (`auth_users`) also dodge Grafana's reserved-word problem with `user` on PostgreSQL.

### 5.6 Taking over the existing `users` table

The existing schema is `users(id, username varchar(32) unique)`, referenced by
`trans_user_flags.user_id` with an **unnamed** foreign key, and HARP's metadata has no
naming convention (`harp_apps/storage/migrations/versions/20240609082234_248285939c4c_initial.py`,
`harp_apps/storage/models/flags.py`).

Options from the sources:

1. **Rename in place** (`users` → `auth_users`) and add columns. PostgreSQL rename "has no
   effect on the stored data" and constraints follow the table
   ([PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)).
   SQLite ≥ 3.26 rewrites foreign-key references in child tables on rename unless
   `legacy_alter_table=ON` ([SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html)).
   MySQL updates foreign keys pointing at the renamed table, failing on constraint-name
   conflicts ([MySQL RENAME TABLE](https://dev.mysql.com/doc/refman/8.4/en/rename-table.html)).
   Widening `username` and adding NOT NULL columns on SQLite goes through Alembic batch
   "move and copy", which cannot target unnamed constraints without a `naming_convention`
   ([Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html)).
   Adding a SQLAlchemy `MetaData(naming_convention=...)` before this migration avoids
   that trap.
2. **Keep the legacy name.** Sentry still lives in `auth_user` and keeps a display-name
   column called `first_name` through `db_column`
   ([user.py#L106-L108](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L106-L108),
   [#L214](https://github.com/getsentry/sentry/blob/86b1728a40fc57fd64ca6fb5e7c892b17c061b8c/src/sentry/users/models/user.py#L214)).
   The ORM class can map `__tablename__ = "users"` and own it from the auth app.
3. **Rename with a compatibility view** (GitLab's zero-downtime technique: rename, create a
   view with the old name, drop the view a release later)
   ([rename_database_tables.md#L10-L23](https://github.com/gitlabhq/gitlabhq/blob/d7b9a6176ab4e279465ba3ee09922cde2b74de47/doc/development/database/rename_database_tables.md?plain=1#L10-L23)).
   Overkill for a single-process proxy but relevant if external readers query `users`.
4. **Create new, copy, drop old** (Grafana's `api_key_v2` pattern,
   [apikey_mig.go#L58-L76](https://github.com/grafana/grafana/blob/ff4c677cdf3f284e49cbc91c958dfa79a41d10d2/pkg/services/sqlstore/migrations/apikey_mig.go#L58-L76)),
   which requires re-pointing `trans_user_flags.user_id`.

Whatever the option: existing rows (including `anonymous`) need a backfill for `kind`,
`role` and `created_at`; GoTrue's backfill of identity rows for existing password users is
the model for creating `auth_identities` rows when needed
([backfill_email_identity.up.sql](https://github.com/supabase/auth/blob/c3348e8f1cb31454e9783e4eb9eab1e71ad9652f/migrations/20221125140132_backfill_email_identity.up.sql#L1-L9)).
Django's warning stands: moving the user table after foreign keys exist is the expensive
case, so make the ownership change once and early.

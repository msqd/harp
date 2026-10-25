# auth: record its audit events

**Problem**

The auth application (epic #1527) changes who can do what, without a trace.

**Acceptance criteria**

- Each action below runs in a unit of work and records its `auditable` event, with the fields of the catalogue (`explorations/audit/catalogue.html`): `auth.signed_in`, `auth.signed_out`, `auth.sessions_revoked`, `auth.invitation.created` (including the setup invitation, actor `system`), `auth.invitation.accepted`, `auth.invitation.revoked`, `auth.account.created` (actor via `cli` from the command line), `auth.account.role_changed`, `auth.account.disabled`, `auth.account.enabled`, `auth.password_changed`, `auth.identity.linked`, `auth.identity.unlinked`, `auth.token.created`, `auth.token.revoked`.
- A refused attempt at any of these by an authenticated account records the same action with outcome `denied` and `required_role` in its details.
- A failed sign-in (form, OIDC callback, Basic, rejected token) emits the `loggable` event `auth.sign_in_failed` with `claimed`, `ip` and `reason`, and no audit row.
- The actor carries the account, `via`, `via_id` and client from the actor context.
- Auth declares `audit` in its dependencies.

**Out of scope**

Basic users import (deprecated path, not recorded).

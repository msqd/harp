# audit: record auditable events in their action's commit

**Problem**

Auditable events need a home that is never shed and never edited, and a copy for the Operator's SIEM.

**Acceptance criteria**

- New application `harp_apps/audit`, with its alembic branch and table `audit_events`: `id`, `occurred_at`, `action`, `outcome` (`succeeded`, `failed`, `denied`), `actor_account_id` (nullable), `actor_via` (`session`, `token`, `cli`, `system`), `actor_via_id`, `actor_client`, `ip`, `user_agent`, `target_type`, `target_id`, `target_label`, `details` (JSON). Indexed for the Audit page filters (period, actor, action, target).
- A transactional listener writes one row per `auditable` event, in the action's unit of work. No route or service updates or deletes a row; the only deletion is retention.
- After commit, each event is written to logger `harp.audit` with the same fields and `kind: audit`.
- Retention: `audit.retention_days`, 365 by default, purged by the janitor, independently of transaction retention.
- Applications that perform critical actions declare `audit` in their `dependencies`; a HARP without them loads no audit.
- No secret ever reaches `details` (test with a token creation event).

**Out of scope**

Hash chaining; the Audit page (child 6).

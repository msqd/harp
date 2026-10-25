# storage: a period-bounded transaction query with a time limit

**Problem**

`get_transaction_list` (`harp_apps/storage/services/sql.py:278`) has no period filter, and its text search is a `LIKE %…%` over every message summary (`:111-124`): nothing bounds what one call can scan. MCP needs bounded searches, and the dashboard's period filter (#1037) needs the same query.

**Acceptance criteria**

- The transaction list accepts `from` and `to` filtering on `started_at` (indexed), with a cursor ordered newest first.
- A caller can bound the query's run time: `statement_timeout` on PostgreSQL, `MAX_EXECUTION_TIME` on MySQL, an asyncio timeout on SQLite; exceeding it raises a dedicated error, not a database exception (test on each database).
- The text search only ever runs inside the period filter when a period is given (query plan or count test).
- #1037 can reuse it: coordinate with its issue and say so there.

**Out of scope**

Full-text indexes.

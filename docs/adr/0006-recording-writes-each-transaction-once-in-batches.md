# ADR-0006: Recording writes each transaction once, in batches, best effort

- **Status**: accepted, not yet implemented outside `explore/extensions`
- **Date**: 2026-10-18
- **Decided in**: [#1364](https://github.com/msqd/harp/issues/1364)

The storage worker writes a transaction once, when it ends: the transaction, its messages and their blobs
together. Ended transactions are flushed in batches, every 1 s or every 500 transactions, whichever comes
first. A transaction still running after 1 s is inserted early, so other instances see it in flight, and its
end updates it. All three numbers are settings.

Recording stays best effort. There is no write-ahead log: a crash loses what was not yet flushed, at most one
batch. Under pressure the worker sheds, as today, by queue length and also by pending payload bytes (64 MiB by
default), and every shed item stays marked on its transaction.

PostgreSQL gets a bulk path. SQLite must keep working, with no speed promise.

## Why

On the `default` profile, recording is 55.6 % of HARP's CPU, and 58 % of that is SQLAlchemy Python code (cache
keys, compilation, ORM unit of work, greenlets) rather than database work. A transaction costs about eight
round trips, each committed: transaction insert, two message inserts, four blob puts, transaction update.
Recording saturates at 100 to 125 req/s, while proxying alone holds 250 req/s. One write per transaction and
one statement per batch remove most of that per-row overhead.

## Rejected

- **Write-ahead log** to survive crashes: the transaction record is observability, not a ledger; a log on the
  request path costs a disk write per transaction to save one second of history.
- **One write per event, kept as is**: the cost above.
- **Rust recorder (tokio) now**: the cost is ORM overhead and round trips, which plain Python removes. It is
  considered again only if recording still costs ≥ 15 % of CPU per request after this lands.

## Consequences

- A transaction is visible in the dashboard up to one flush interval after it ends, and up to the early-insert
  threshold after it starts.
- Memory holds up to one batch of pending transactions and their payloads; the byte limit bounds it.
- On shutdown the worker flushes what is pending.
- Blobs are deduplicated within a batch. The orphan-grace guarantee of the blob storage still holds: a blob is
  renewed in the same database transaction as the message that references it.

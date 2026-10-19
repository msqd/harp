# ADR-0005: PostgreSQL is the production database; MySQL and MariaDB are deprecated

- **Status**: accepted
- **Date**: 2026-10-19
- **Decided in**: [#1383](https://github.com/msqd/harp/issues/1383)

PostgreSQL is the only database supported in production. SQLite is for development. MySQL and MariaDB
are deprecated from 0.12: they keep working and stay tested in CI, with no production support and no
performance commitment, and will be removed in a future version (not decided). HARP logs a one-line
warning at boot when `storage.url` is a MySQL or MariaDB URL.

## What was actually being decided

The docs presented SQLite, PostgreSQL and MySQL/MariaDB side by side, as equals. They are not. PostgreSQL
is the database we benchmark and run. SQLite is convenient for development. MySQL and MariaDB cost a CI
job, dialect-specific code (text search, migrations) and support effort, for no production commitment on
our side.

## Rejected

- **Remove MySQL and MariaDB now.** Breaks existing deployments in a minor release. Deprecating first
  gives operators a release to move.
- **Keep all three as equals.** Promises behaviour and performance we do not measure.
- **Document it without a boot warning.** Operators do not re-read the storage page; the log line is
  where they see it.

## Consequences

- Benchmarks and behaviour guarantees target PostgreSQL.
- MySQL and MariaDB are removed in a future version. The version is not decided; this record is
  superseded when it is.
- The boot warning never prints the URL: it may carry a password.

# Architecture decision records

One file per decision that outlives the ticket that prompted it. A record says what was decided, why,
and what was rejected, so that the reasoning is available to whoever inherits the consequence. Records
are not edited to match later decisions: a decision that is reversed gets a new record, and the old one
stays with its status changed.

| | Decision | Status |
|---|---|---|
| [0001](./0001-compliant-by-default-operator-may-override.md) | Compliant by default, and the operator may override anything | accepted |
| [0002](./0002-caller-no-store-suppresses-payload-recording.md) | A caller's `no-store` suppresses payload recording, but not the record that traffic happened | accepted, not yet implemented |
| [0003](./0003-cache-compliance-compared-per-test-against-a-pinned-baseline.md) | RFC 9111 compliance is compared per test id against a baseline pinned to its storage backend | accepted |
| [0004](./0004-trunk-main-and-version-line-branches.md) | Development happens on `main`; a version line gets its branch when it ships | accepted |
| [0005](./0005-postgresql-production-database.md) | PostgreSQL is the production database; MySQL and MariaDB are deprecated | accepted |
| [0009](./0009-credentials-redacted-before-storage-by-rule.md) | Credentials are redacted before storage, by rule, and credential headers are redacted by default | accepted, not yet implemented |
| [0010](./0010-harp-credentials-never-reach-an-origin.md) | HARP's own credentials never reach an origin, and no setting changes that | proposed |
| [0011](./0011-each-app-owns-an-alembic-branch.md) | Each application owns a branch of one alembic history | proposed |
| [0012](./0012-critical-actions-recorded-in-their-own-commit.md) | A critical action and its audit event share one commit, through a two-phase unit of work | proposed |

## Writing one

Number it in sequence, name the file after the decision rather than the problem, and open with the
title and a three-line header:

```markdown
# ADR-0003: The decision, stated as a sentence

- **Status**: accepted
- **Date**: 2026-08-17
- **Decided in**: [#927](https://github.com/msqd/harp/issues/927)
```

Plain Markdown rather than YAML frontmatter, deliberately. GitHub's file view turns leading frontmatter
into a table, but its own `/markdown` API and most other renderers do not: they emit a horizontal rule
and a heading made of the metadata, which is how the first draft of these records rendered. A list
renders the same way everywhere.

`status` is one of `proposed`, `accepted`, `accepted, not yet implemented`, `superseded by ADR-nnnn` or
`rejected`. A decision that is accepted but not yet built says so, and says under its title which
release it applies from, so nobody reads it as a description of the version they are running.

The vocabulary these records use is defined in [`CONTEXT.md`](../../CONTEXT.md) at the repository root.

## Why these are not in the built documentation

Deliberately outside the Sphinx tree. These are contributor artifacts, read in the repository by people
working on HARP, and GitHub renders them as they are. `docs/conf.py` does not enable `myst_parser`, so
no Markdown under `docs/` is rendered today, and `docs/contribute/release/dockerhub-setup.md` already
sits here on the same terms.

Publishing them is a separate decision about enabling MyST across the documentation, and it should be
taken on its own terms rather than as a side effect of adding a record.

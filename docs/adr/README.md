# Architecture decision records

One file per decision that outlives the ticket that prompted it. A record says what was decided, why,
and what was rejected, so that the reasoning is available to whoever inherits the consequence. Records
are not edited to match later decisions: a decision that is reversed gets a new record, and the old one
stays with its status changed.

| | Decision | Status |
|---|---|---|
| [0001](./0001-compliant-by-default-operator-may-override.md) | Compliant by default, and the operator may override anything | accepted |
| [0002](./0002-caller-no-store-suppresses-payload-recording.md) | A caller's `no-store` suppresses payload recording, but not the record that traffic happened | accepted, not yet implemented |

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

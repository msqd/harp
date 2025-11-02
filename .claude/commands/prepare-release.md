---
allowed-tools: Bash(git:*)
description: Prepare a future $ARGUMENTS release.
---

We want to prepare the next release (either "$ARGUMENTS", if empty try to read VERSION variable).

For that, we need to move all changelog entries from `docs/changelogs/unreleased.rst` to
`docs/changelogs/VERSION.rst`.

Look at other changelogs to understand formating, the title should be
"Version a.b.c (YYYY-MM-DD)", and the date should be retrieved using the "date" binary
(system date).

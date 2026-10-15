# ADR-0004: Development happens on `main`; a version line gets its branch when it ships

- **Status**: accepted
- **Date**: 2026-10-15
- **Decided in**: [0.11 kickoff](https://github.com/msqd/harp/milestone/11)

`main` is the permanent default branch, where the next version is built. A release is a tag. At each
`X.Y.0` release, a branch `X.Y` is created on the tag: it serves `/en/X.Y/` on Read the Docs and
receives backports for patch releases. Version-line branches are never deleted, and only the latest
line receives patches.

## What was actually being decided

Until 0.10, each version line was the default branch while it was developed (`0.8`, `0.9`, `0.10`),
and the default was switched by hand when the next line opened. Nothing described when that happened,
who did it, or what moved with it: open pull requests, Dependabot, the docs' `latest`, the Docker
`X.Y-git` images. The day 0.10.0 shipped, the next version had nowhere to land but the branch that had
just been released.

The version lines were never used for what they promise. No release was ever cut from a line after
the next one opened: no backport, no 0.8.2, no 0.9.2. `0.9` has one commit `0.10` does not; `0.10` has
269 that `0.9` does not.

## The model

- **`main`**: the default branch; it never changes. Every pull request targets it unless it is a
  backport. Right after `X.Y.0` is tagged, `main` moves to version `X.Y+1.0.dev0`.
- **Version line `X.Y`**: a branch created on the `X.Y.0` tag at release time. It moves only through
  backports, and freezes once `X.Y+1.0` ships.
- **Patch release**: only on the latest version line, for bugs and security, never features. The
  product owner proposes it, the user decides it, and it follows the release flow.
- **Backport**: the fix merges into `main` first, then a pull request cherry-picks it (`git cherry-pick
  -x`) onto `X.Y`. A fix that no longer applies to `main` goes to `X.Y` directly, and its pull request
  says why.
- **Protection**: `main` and every `X.Y` require a pull request and a green *All Checks Passed*, for
  administrators too, with no force-push or deletion. A release goes through a release pull request.
- **Docs**: `latest` serves `main`, `stable` the highest release tag, `/en/X.Y/` each line's branch.
  The Read the Docs version warnings mark `latest` as unreleased and every other version as not the
  stable one. The dashboard's Help link opens `/en/X.Y/` for a release and `/en/latest/` for a
  development build.
- **Docker**: a push to `main` publishes the `unstable` image, a push to `X.Y` publishes `X.Y-git`;
  release images are published from tags, unchanged.

## Rejected

- **Keep switching the default branch per version line, and document it.** Every switch moves open
  pull requests, Dependabot and the docs' `latest`, and the history shows the old line is never
  patched afterwards. A documented chore is still a chore that gets skipped.
- **Branch only when a patch is needed.** Cheaper, but Read the Docs builds a slug from a branch or a
  tag only, so `/en/X.Y/` would either not exist or need a hand-maintained alias at every release.
- **Our own banner in `docs/conf.py`.** It is decided at build time, and a frozen branch is never
  rebuilt, so an old line could never switch itself to "older version". It also marked every slug but
  `latest` as unreleased, including `0.10` the day it shipped.
- **Delete old lines.** Their docs, and the Help links of installations still running them, would
  break.

## Consequences

- The release runbook (`docs/contribute/release/python.rst`) gains three steps: release pull request
  before the tag, `X.Y` branch and its protection after an `X.Y.0` tag, and the pull request opening
  `X.Y+1.0.dev0` on `main`.
- `docs/contribute/branching.rst` states the model; this record states why.

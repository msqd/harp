---
allowed-tools: Bash(git:*)
description: Update the unreleased changes in the changelog.
---

# What is a changelog?

A changelog is a file which contains a curated, chronologically ordered list of notable
changes for each version of a project. We keep it updated to make it easier for users and
contributors to see precisely what notable changes have been made between each release
(or version) of the project. People need a changelog. Whether consumers or developers, the
end users of software are human beings who care about what's in the software. When the
software changes, people want to know why and how.

* Changelogs are for humans, not machines.
* The same types of changes should be grouped.
* We try our best to follow Semantic Versioning.

## Types of changes

* `Added` for new features.
* `Changed` for changes in existing functionality.
* `Deprecated` for soon-to-be removed features.
* `Removed` for now removed features.
* `Fixed` for any bug fixes.
* `Security` in case of vulnerabilities.

## Files and path

We keep changelogs in `docs/changelogs`. We have one file per version, which won't change
once released, and the most important file of interest is `docs/changelogs/unreleased.rst`,
which contains all changes that are not yet released.

Read the current git index and the commits since the last unreleased.rst update and update
the `unreleased.rst` file with short, concise informations about the changes.

Start with the git staged changes, user may just want to update what he just did.

## Dependencies versions

For dependencies updates, look at:

* pyproject.toml and uv.lock for backend
* harp_apps/dashboard/frontend/package.json and harp_apps/dashboard/frontend/pnpm-lock.yaml
  for frontend

Include one unreleased line per dependency upgrade::

    * Bump package-name: old-version → new-version

Version numbers should not be version ranges, only the locked/pinned version should be
shown in the bump line.

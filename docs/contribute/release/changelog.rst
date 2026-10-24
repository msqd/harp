Changelog
=========

HARP maintains a changelog following the `Keep a Changelog <https://keepachangelog.com/>`_ format. All changes are tracked in version-specific files in ``docs/changelogs/``.

Overview
--------

Entries are `towncrier <https://towncrier.readthedocs.io/>`_ fragments: one small file per pull
request in ``changelog.d/``, so two pull requests never edit the same file and never conflict. The
release manager assembles the fragments into ``docs/changelogs/X.Y.Z.rst`` when cutting the final
``X.Y.Z``. A pre-release (``-alphaN``, ``-betaN``, ``-rcN``) leaves the fragments in place: its GitHub
release notes are rendered from them, and the final release still needs them.

1. **During development**: Add a fragment to ``changelog.d/`` in your pull request
2. **Before release**: Build the fragments into a version-specific file (e.g., ``0.11.0.rst``)
3. **After release**: The version-specific changelog appears in the GitHub Release

The documentation build renders the pending fragments as the *unreleased* changelog page
(``docs/changelogs/unreleased.rst``, generated and git-ignored), titled with the version read from
``pyproject.toml``. Without a pending fragment, the page does not exist.

When to Add Entries
-------------------

Add a fragment **per Pull Request**:

* Before merging a PR, ensure ``changelog.d/`` contains a fragment for your changes
* If a PR contains multiple distinct changes, add multiple fragments
* Each entry should describe **what changed** from a user/contributor perspective

Do NOT add entries for:

* Minor typo fixes in documentation
* Internal refactoring with no external impact
* Dependency updates (unless they fix a critical issue)

Categories
----------

Entries are organized into these categories:

**Important Changes**
  Breaking changes or significant modifications requiring attention.

  Use this sparingly - only for changes that **require action** from users.

**Added**
  New features, capabilities, or documentation.

  Examples:

  * Version validation in release workflow
  * Support for Python 3.14 free-threaded mode
  * New ``bin/validate_version`` script

**Changed**
  Changes to existing functionality.

  Examples:

  * Updated release workflow to require manual version bumps
  * Migrated from Poetry to UV package manager
  * Bump dependency: ``alembic: 1.15.2 → 1.17.0``

**Fixed**
  Bug fixes.

  Examples:

  * Fixed race condition in transaction storage
  * Corrected timezone handling in dashboard

**Security**
  Security fixes. Keep the entry terse: state that something was fixed, never how it could be exploited
  (see :doc:`../branching`).

**Removed**
  Removed features or dependencies.

  Examples:

  * Removed Poetry dependency
  * Removed deprecated ``--legacy`` flag

**Tooling**
  CI, test and build tooling changes. Rendered nowhere in the release notes: use it for entries that
  matter to contributors only.

  Examples:

  * CI runs the storage suite against MySQL in its own job
  * Test runner pins plain output

Type by impact on operators, not by the kind of work. A fix that changes what an operator observes (a new
status code, a cap, a timeout, data kept or deleted) is ``important``, and is listed in the
upgrade notes of the release (see :ref:`upgrading-0-12`).

How to Add an Entry
-------------------

Create ``changelog.d/<issue>.<category>.rst`` holding the one-line entry, where ``<category>`` is
one of ``important``, ``added``, ``changed``, ``fixed``, ``security``, ``removed`` or ``tooling``:

.. code-block:: bash

    echo 'Support for Python 3.14t (free-threaded/no-GIL).' > changelog.d/123.added.rst

The issue number is appended to the entry as ``(#123)``. A change without an issue uses a name
starting with ``+`` and any slug, which renders no reference: ``changelog.d/+python-314t.added.rst``.
A second fragment for the same issue and category takes a counter: ``123.added.1.rst``.

Preview the result with:

.. code-block:: bash

    uv run towncrier build --draft --version 0.11.0

Commit the fragment with your changes.

Writing Good Entries
--------------------

**Good entries** are:

* **User-focused**: Describe the impact, not the implementation
* **Concise**: One line per change
* **Specific**: Clear about what changed

Examples:

.. code-block:: rst

   ✅ Good:
   * Added version validation to prevent tag/version mismatches
   * Fixed dashboard crash when viewing large transactions
   * Removed support for Python 3.11

   ❌ Bad:
   * Updated code
   * Fixed bug in src/storage/models.py line 42
   * Refactored validation logic (too vague)

For breaking changes, be explicit:

.. code-block:: rst

   Important Changes
   :::::::::::::::::

   * ⚠️ Release workflow now requires manual version updates in pyproject.toml
     before tagging. The CI no longer modifies versions automatically.

Changelog Format
----------------

The assembled changelog follows this structure (empty categories are omitted):

.. code-block:: rst

   Version 0.11.0 (2026-10-30)
   ===========================

   Important Changes
   :::::::::::::::::

   - ⚠️ Breaking change description with warning emoji

   Added
   :::::

   - New feature 1 (#123)

   Changed
   :::::::

   - Changed behavior 1

   Fixed
   :::::

   - Bug fix 1

   Security
   ::::::::

   - Security fix 1

   Removed
   :::::::

   - Removed feature 1

Before Release (Release Manager)
---------------------------------

The release manager performs these steps before creating a release:

1. **Review pending fragments**

   Check that all entries in ``changelog.d/`` are clear, properly categorized, and user-focused.

2. **Build the version-specific file** (final release only, never for a pre-release)

   .. code-block:: bash

      # For version 0.9.0
      uv run towncrier build --draft --version 0.9.0 --date 2025-01-15 > docs/changelogs/0.9.0.rst
      git rm changelog.d/*.*.rst

   The ``changelog.d/README.rst`` file stays. After a patch release, the pull request that brings
   ``X.Y.Z.rst`` to ``main`` also runs ``git rm`` on the fragments that patch shipped, so the next
   ``X.Y+1.0`` lists only what is new since. Security entries are the exception: ``X.Y+1.0`` repeats those of the
   patches shipped since ``X.Y.0``, with their advisory ids, so a reader upgrading across the patches sees
   them. Check the first lines of the new file: the ``Version
   X.Y.Z (date)`` title and its underline must come first.

3. **Update changelog index**

   Add the new version to ``docs/changelogs/index.rst``, below ``unreleased``:

   .. code-block:: rst

      .. toctree::
         :maxdepth: 1

         unreleased
         0.9.0
         0.8.0
         ...

4. **Commit changelog updates**

   .. code-block:: bash

      git add docs/changelogs/ changelog.d/
      git commit -m "docs: prepare changelog for 0.9.0"

The GitHub Release workflow automatically converts the RST changelog to Markdown and includes it in the GitHub Release.

See Also
--------

* :doc:`python` - Complete release process
* `Keep a Changelog <https://keepachangelog.com/>`_ - Changelog format specification

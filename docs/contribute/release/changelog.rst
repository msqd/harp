Changelog Management
====================

HARP maintains a changelog following the `Keep a Changelog <https://keepachangelog.com/>`_ format. All changes are tracked in version-specific files in ``docs/changelogs/``.

Overview
--------

The changelog workflow:

1. **During development**: Add entries to ``docs/changelogs/unreleased.rst``
2. **Before release**: Move unreleased changes to a version-specific file (e.g., ``0.9.0.rst``)
3. **After release**: The version-specific changelog appears in the GitHub Release

When to Add Entries
-------------------

Add changelog entries **per Pull Request or per feature/bugfix**:

* Before merging a PR, ensure the unreleased changelog contains entries for your changes
* If a PR contains multiple distinct changes, add multiple entries
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

**Removed**
  Removed features or dependencies.

  Examples:

  * Removed Poetry dependency
  * Removed deprecated ``--legacy`` flag

How to Add an Entry
-------------------

1. Open ``docs/changelogs/unreleased.rst``

2. Add your entry under the appropriate category:

   .. code-block:: rst

      Added
      -----

      * Your new feature description here
      * Support for Python 3.14t (free-threaded/no-GIL)

3. If a category doesn't exist yet, create it following the structure:

   .. code-block:: rst

      Category Name
      -------------

      * Your entry here

4. Commit the changelog with your changes:

   .. code-block:: bash

      git add docs/changelogs/unreleased.rst
      git commit -m "docs: update changelog for feature X"

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

The unreleased changelog follows this structure:

.. code-block:: rst

   Unreleased
   ==========

   Important Changes
   :::::::::::::::::

   * ⚠️ Breaking change description with warning emoji

   Added
   -----

   * New feature 1
   * New feature 2

   Changed
   -------

   * Changed behavior 1
   * Dependency update: package: old → new

   Fixed
   -----

   * Bug fix 1

   Removed
   -------

   * Removed feature 1

Before Release (Release Manager)
---------------------------------

The release manager performs these steps before creating a release:

1. **Review unreleased changes**

   Check that all entries are clear, properly categorized, and user-focused.

2. **Move to version-specific file**

   .. code-block:: bash

      # For version 0.9.0
      mv docs/changelogs/unreleased.rst docs/changelogs/0.9.0.rst

3. **Add version header and date**

   Edit the new file to add the version and release date:

   .. code-block:: rst

      0.9.0 (2025-01-15)
      ==================

      Important Changes
      :::::::::::::::::
      ...

4. **Create new empty unreleased file**

   .. code-block:: bash

      cat > docs/changelogs/unreleased.rst <<EOF
      Unreleased
      ==========

      Important Changes
      :::::::::::::::::

      Added
      -----

      Changed
      -------

      Fixed
      -----

      Removed
      -------
      EOF

5. **Update changelog index**

   Add the new version to ``docs/changelogs/index.rst``:

   .. code-block:: rst

      .. toctree::
         :maxdepth: 1

         unreleased
         0.9.0
         0.8.0
         ...

6. **Commit changelog updates**

   .. code-block:: bash

      git add docs/changelogs/
      git commit -m "docs: prepare changelog for 0.9.0"

The GitHub Release workflow automatically converts the RST changelog to Markdown and includes it in the GitHub Release.

See Also
--------

* :doc:`python` - Complete release process
* `Keep a Changelog <https://keepachangelog.com/>`_ - Changelog format specification

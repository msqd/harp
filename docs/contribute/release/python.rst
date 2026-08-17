Python Package
==============

This guide describes the complete process for releasing a new HARP version to PyPI.

.. danger::

    **This page tells you how to cut a release. It does not tell you whether you may.**

    A release is not tagged until the user has signed off on the product owner's recette. If nobody
    has told you that happened, stop here and ask, however green the tests are and however empty the
    pull-request queue is. Read :doc:`validation` first.

    This matters most if you picked the release up mid-flight, from a handover or a lost session,
    because nothing on this page would otherwise stop you. Publishing to PyPI cannot be undone.

.. note::

    The release process is fully automated via GitHub Actions. When you push a version tag,
    the workflow automatically builds, tests, and publishes the package.

Prerequisites
-------------

Before creating a release, ensure:

* You have push access to the GitHub repository
* All changes are merged to the ``main`` or version branch (e.g., ``0.9``)
* All CI tests are passing
* PyPI trusted publishing is configured (see `PyPI Trusted Publishing Guide <https://docs.pypi.org/trusted-publishers/>`_)

Quick Overview
--------------

The automated release workflow handles:

1. **Version validation** - Ensures ``pyproject.toml`` version matches the git tag
2. **Package building** - Builds wheel in isolated sandbox environment with frontend bundled
3. **Testing** - Tests installation on Python 3.13, 3.14, and 3.14t (free-threaded)
4. **Publishing** - Publishes to TestPyPI, then production PyPI
5. **GitHub Release** - Creates release with changelog and wheel artifacts

Who does what, and when
-----------------------

.. important::

    **The version number and the release date are set by the release engineer, at cut time, and by
    nobody else.**

    Steps 2 to 5 below (the changelog date, the ``pyproject.toml`` version and the ``uv.lock``
    refresh) belong to the person cutting the release, at the moment they cut it. They are not
    preparatory work, and they do not belong in a feature branch or in a pull request that is
    waiting to merge.

    The reason is that both values are claims about when the release happened. A version bumped
    before the last pull request lands, or a date stamped a week before the tag, is wrong by the
    time anyone reads it, and the version validation step of the automated workflow will reject a
    ``pyproject.toml`` that has drifted from the tag.

    While a release is being prepared, the version stays at its pre-release value
    (``X.Y.Z-alphaN``, ``X.Y.Z-rcN``) and the changelog header stays ``Version X.Y.Z
    (unreleased)``. Contributors preparing changes for the release add changelog *entries*, never
    the version or the date.

Step-by-Step Release Process
-----------------------------

Steps 1 to 5 are the release engineer's, performed at cut time and in one sitting. If you are not
cutting the release right now, stop here: see `Who does what, and when`_ above.

1. Does this release carry a database migration?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Answer this before touching the changelog, because the answer changes what the changelog has to say.

List the migration revisions added since the previous release:

.. code-block:: bash

    # Replace 0.9.1 with the tag of the previous release
    git diff --name-only 0.9.1..HEAD -- harp_apps/storage/migrations/versions/

**No output means no migration**, and there is nothing more to do in this step. Any output names the
revisions this release introduces.

If the release does carry one:

* **Read the revision** and work out what it does to existing data. A column that widens is not the
  same risk as a column that narrows, a type that changes, or a constraint that is added.
* **Check that the changelog says so**, in *Important Changes*, and that it says which backends are
  affected. HARP applies migrations itself on startup when ``storage.migrate`` is enabled, which is
  the default, so an operator on the default path has nothing to run. The manual
  ``harp-proxy db:migrate up head`` step is for operators who set ``storage.migrate: false``, and
  that is the case any warning about breakage should be attached to. See
  :doc:`/apps/storage/index` for the behaviour.
* **Say whether the previous version still runs against the new schema.** If it does not, a rollback
  is not just a matter of reinstalling the old wheel, and the changelog is where somebody finds that
  out before they need it rather than after.

.. note::

    Do not write this step's findings as a description of the current migration. The next release's
    migration will be a different one. Answer the question again each time.

2. Prepare the Changelog
~~~~~~~~~~~~~~~~~~~~~~~~~

The version's changelog file usually exists already, carrying an ``(unreleased)`` header, because
contributors have been adding entries to it while the release was prepared. In that case do not
move anything: edit the header in place and replace ``(unreleased)`` with today's date.

.. code-block:: rst

    Version 0.9.0 (2025-01-15)
    ==========================

The ``Version `` prefix is part of the convention, and the ``=`` underline must be at least as long
as the title. Match the two exactly, as the existing changelogs do.

.. warning::

    Nothing in the build will tell you if you get this wrong. A malformed title or a short underline
    is not reported by ``make docs``, so check the rendered page yourself.

If the version has no changelog file yet, create one by moving the accumulated entries into it, then
add the header above:

.. code-block:: bash

    # For version 0.9.0
    mv docs/changelogs/unreleased.rst docs/changelogs/0.9.0.rst

Either way, make sure an empty ``unreleased.rst`` is left in place for the next cycle.

See :doc:`changelog` for complete changelog management workflow.

Commit the changelog updates:

.. code-block:: bash

    git add docs/changelogs/
    git commit -m "docs: prepare changelog for 0.9.0"

3. Set the Version Number
~~~~~~~~~~~~~~~~~~~~~~~~~~

Define the version as an environment variable to avoid typos:

.. code-block:: bash

    export VERSION=0.9.0

For pre-releases, use appropriate suffixes:

.. code-block:: bash

    export VERSION=0.9.1-rc1    # Release candidate
    export VERSION=1.0.0-beta1  # Beta release
    export VERSION=1.0.0-alpha1 # Alpha release

4. Update pyproject.toml
~~~~~~~~~~~~~~~~~~~~~~~~~

Update the version in ``pyproject.toml`` and verify:

.. code-block:: bash

    sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml && rm pyproject.toml.bak
    uv lock
    grep "^version" pyproject.toml

5. Commit the Version Change
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git add pyproject.toml uv.lock
    git commit -m "chore: bump version to $VERSION"

6. Create an Annotated Git Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. danger::

    **Last stop. Has the user signed off?**

    Pushing this tag publishes to PyPI, and PyPI does not allow a version number to be reused. The
    sign-off is the user's, on the product owner's recette, and it is not something you can infer
    from green CI or an empty queue. If you cannot point to it having happened, do not tag. See
    :doc:`validation`.

.. code-block:: bash

    git tag -a $VERSION -m "Release $VERSION"

.. important::

    Always use the ``-a`` flag to create an **annotated tag**, not a lightweight tag.
    The release workflow requires annotated tags.

7. Push Changes and Tag
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git push origin
    git push origin $VERSION

.. note::

    Push the tag **after** pushing the commit to ensure the tag points to the correct commit.

8. Monitor the Release Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the tag is pushed, GitHub Actions automatically runs the release workflow:

.. code-block:: text

    1. Validates that pyproject.toml version matches tag
       └─ Fails if versions don't match (see Troubleshooting)

    2. Builds wheel in sandbox environment
       ├─ Installs dependencies
       ├─ Builds React frontend
       ├─ Bundles static assets
       └─ Creates wheel with twine validation

    3. Tests the built wheel
       ├─ Python 3.13 (standard)
       ├─ Python 3.14 (standard)
       └─ Python 3.14t (free-threaded/no-GIL)

    4. Publishes to TestPyPI
       └─ For validation before production

    5. Publishes to PyPI
       └─ Production release

    6. Creates GitHub Release
       ├─ Converts changelog (RST → Markdown)
       ├─ Attaches wheel artifacts
       └─ Marks as pre-release if applicable

Watch the workflow progress:

.. code-block:: bash

    # Using GitHub CLI
    gh run list --limit 5
    gh run watch  # Watch the latest run

Or visit: ``https://github.com/msqd/harp/actions``

The workflow typically takes 10-15 minutes to complete.

9. Verify the Release
~~~~~~~~~~~~~~~~~~~~~~

Once the workflow completes successfully:

**Check PyPI:**

.. code-block:: bash

    # View on PyPI
    open https://pypi.org/project/harp-proxy/

**Check GitHub Release:**

.. code-block:: bash

    # View releases
    open https://github.com/msqd/harp/releases

**Test Installation:**

.. code-block:: bash

    # Test directly from PyPI without installing (recommended)
    uvx harp-proxy@$VERSION version

    # Run commands to verify functionality
    uvx harp-proxy@$VERSION --help

    # Download the wheel file without installing
    # Direct download from PyPI using JSON API (no pip required)
    curl -L $(curl -s https://pypi.org/pypi/harp-proxy/$VERSION/json | \
      python3 -c "import sys, json; print([u['url'] for u in json.load(sys.stdin)['urls'] if u['packagetype']=='bdist_wheel'][0])") \
      -o harp_proxy-$VERSION-py3-none-any.whl
    # Or with jq (if installed)
    curl -L $(curl -s https://pypi.org/pypi/harp-proxy/$VERSION/json | \
      jq -r '.urls[] | select(.packagetype=="bdist_wheel") | .url') \
      -o harp_proxy-$VERSION-py3-none-any.whl

    # For persistent installation in a project
    uv pip install harp-proxy==$VERSION

Version Naming Conventions
---------------------------

Follow semantic versioning:

**Stable Releases**
  ``X.Y.Z`` (e.g., ``0.9.0``, ``1.0.0``, ``2.1.3``)

  Use for production-ready releases.

**Release Candidates**
  ``X.Y.Z-rcN`` (e.g., ``0.9.1-rc1``, ``0.9.1-rc2``)

  Use for testing before final release. The workflow automatically marks these as pre-releases.

**Beta Releases**
  ``X.Y.Z-betaN`` (e.g., ``1.0.0-beta1``)

  Use for feature-complete but not fully tested releases.

**Alpha Releases**
  ``X.Y.Z-alphaN`` (e.g., ``1.0.0-alpha1``)

  Use for early testing releases with incomplete features.

Troubleshooting
---------------

Version Mismatch Error
~~~~~~~~~~~~~~~~~~~~~~

If the workflow fails with:

.. code-block:: text

    ❌ Version mismatch!
    Expected (from git tag): 0.9.0
    Actual (from pyproject.toml): 0.9-dev

**Solution:**

1. Delete the tag locally and remotely:

   .. code-block:: bash

      git tag -d $VERSION
      git push origin :refs/tags/$VERSION

2. Fix the version in ``pyproject.toml``

3. Repeat from step 4 (Update pyproject.toml)

Workflow Build Failures
~~~~~~~~~~~~~~~~~~~~~~~~

If the build fails:

1. **Check the workflow logs** for specific errors
2. **Fix the issue** in your code
3. **Delete the failed tag** (see above)
4. **Re-run** the release process

Test Failures
~~~~~~~~~~~~~

If tests fail on specific Python versions:

1. **Review test logs** to identify the issue
2. **Fix the code** to support all Python versions
3. **Re-release** with a new tag

PyPI Publishing Failures
~~~~~~~~~~~~~~~~~~~~~~~~~

The workflow uses PyPI's trusted publishing (OIDC), which requires no manual credentials.

If publishing fails:

1. **Verify trusted publisher configuration** on PyPI:

   * Go to https://pypi.org/manage/account/publishing/
   * Ensure ``harp-proxy`` has a trusted publisher for:

     * Owner: ``msqd``
     * Repository: ``harp``
     * Workflow: ``release.yml``
     * Environment: ``pypi`` and ``testpypi``

2. See the `PyPI Trusted Publishing Guide <https://docs.pypi.org/trusted-publishers/>`_ for setup instructions

Emergency Rollback
~~~~~~~~~~~~~~~~~~

If a release has critical issues:

.. warning::

    **Never delete a PyPI release.** PyPI does not allow re-uploading the same version number.

Instead:

1. **Release a new patch version** with the fix:

   .. code-block:: bash

      export VERSION=0.9.1  # Increment version
      # Follow normal release process

2. **Optionally yank the problematic version** on PyPI:

   * Go to https://pypi.org/project/harp-proxy/
   * Select the problematic version
   * Click "Options" → "Yank release"
   * Provide reason: *"Critical bug, use version X.Y.Z instead"*

   Yanking prevents new installations but doesn't break existing ones.

3. **Update documentation** to warn users about the problematic version

Manual Testing (Before Release)
--------------------------------

To test the build process locally before creating a release:

Build the Wheel
~~~~~~~~~~~~~~~

.. code-block:: bash

    make clean-dist wheel

This command:

* Builds in an isolated sandbox environment
* Compiles and bundles the React frontend
* Creates the wheel package
* Validates with ``twine check``

The wheel is created in ``dist/``.

Test the Wheel
~~~~~~~~~~~~~~

Test the built wheel in a fresh container:

.. code-block:: bash

    bin/runc_wheel dist/*.whl

This starts a container with the wheel installed. Test it:

.. code-block:: bash

    harp-proxy server --endpoint httpbin=4000:http://httpbin.org/

Manual Upload (Emergency Only)
-------------------------------

If the automated workflow is completely broken and you need to release urgently:

.. code-block:: bash

    twine upload dist/*

.. warning::

    This requires PyPI credentials configured locally and should be avoided.
    Always prefer fixing the automated workflow instead.

Best Practices
--------------

* **Test thoroughly before releasing** - Run the full test suite locally
* **Use release candidates for major versions** - Create ``X.Y.Z-rc1`` before ``X.Y.Z``
* **Keep the changelog updated** - Add entries per PR/feature (see :doc:`changelog`)
* **Document breaking changes clearly** - Use "Important Changes" section
* **Release often** - Small, frequent releases are better than large, infrequent ones
* **Monitor after release** - Watch for issues reported after release

See Also
--------

* :doc:`changelog` - Changelog management workflow
* :doc:`chores` - Pre-release housekeeping tasks
* :doc:`../ci` - CI/CD pipeline documentation
* `PyPI Trusted Publishing Guide <https://docs.pypi.org/trusted-publishers/>`_ - PyPI setup reference

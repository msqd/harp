Releasing a new source version
==============================

1. Pull and check dependencies are there.

.. code-block:: shell

    git pull --tags
    make install-dev

2. Generate next version number

.. code-block:: shell

    poetry version <patch|minor|major|prepatch|preminor|premajor|prerelease>
    # ... or edit the version in pyproject.toml

.. code-block:: shell

    export VERSION=`poetry version --short`
    export OLD_VERSION=`git describe --tags --abbrev=0`
    echo New version: $VERSION - Old version: $OLD_VERSION

3. Update version numbers in other project files...

.. code-block:: shell

    gsed -i -e "s/^__version__ = .*/__version__ = \"$VERSION\"/" harp/__init__.py
    gsed -i -e "s/^appVersion: .*/appVersion: \"$VERSION\"/" misc/helm/charts/harp-proxy/Chart.yaml

4. Generate a changelog...

.. code-block:: shell

    git log --oneline --no-merges --pretty=format:"* %s (%an)" $OLD_VERSION.. > docs/contribute/changelogs/$VERSION.rst
    git add docs/contribute/changelogs/$VERSION.rst

5. Reboot computer (yes, we'll get better but that's the easiest way to have reproductible benchmarks for now) and run
   the benchmarks on new version

.. code-block:: shell

    poetry run make benchmark-save

.. todo:: use poetry version for benchmark save ?

.. warning:: benchmarks are broken for now, but we'll re-add it soon.

- **Edit the changelog index** (`docs/contribute/changelogs/index.rst`) to add the new version (title, date).
- **Add a title** to the new changelog file.
- **Add the performance graphs** to the release note.

6. Add to git

.. code-block:: shell

    poetry run make preqa
    git add docs/reference
    git add -p

7. Run a full test suite again (todo: from a clean virtualenv)

.. todo::

    - This should be done from a clean virtualenv, but it's not yet the case (mitigated for now by using a clean git
      worktree on each release, but this is undocumented for now).

Git add is there to check nothing was modified by QA suite.

.. code-block:: shell

   poetry run make qa
   git add -p

8. Create the git release

.. code-block:: shell

    git commit -m "release: $VERSION"

9. Tag and push

.. code-block:: shell

    git tag -am "release: $VERSION" $VERSION

.. code-block:: shell

    git push origin `git rev-parse --abbrev-ref HEAD` --tags

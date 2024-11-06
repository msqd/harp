Releasing a new source version
==============================

Pull and check dependencies
:::::::::::::::::::::::::::

.. code-block:: shell

    git pull --tags
    make install-dev

Generate next version number
::::::::::::::::::::::::::::

.. code-block:: shell

    poetry version <patch|minor|major|prepatch|preminor|premajor|prerelease>
    # ... or edit the version in pyproject.toml

.. code-block:: shell

    export VERSION=`poetry version --short`
    export OLD_VERSION=`git describe --tags --abbrev=0`
    echo New version: $VERSION - Old version: $OLD_VERSION

Update version numbers
::::::::::::::::::::::

.. code-block:: shell

    gsed -i -e "s/^__version__ = .*/__version__ = \"$VERSION\"/" harp/__init__.py
    gsed -i -e "s/^appVersion: .*/appVersion: \"$VERSION\"/" misc/helm/charts/harp-proxy/Chart.yaml

Additionally, bumb the chart version in ``misc/helm/charts/harp-proxy/Chart.yaml``:

.. code-block:: shell

    vi misc/helm/charts/harp-proxy/Chart.yaml

Generate a changelog
::::::::::::::::::::

.. code-block:: shell

    git log --oneline --no-merges --pretty=format:"* %s (%an)" $OLD_VERSION.. > docs/changelogs/$VERSION.rst
    git add docs/changelogs/$VERSION.rst

- **Move the unreleased changes** (:code:`vi docs/changelogs/unreleased.rst`)
- **Edit the changelog index** (`docs/changelogs/index.rst`) to add the new version (title, date).
- **Add a title** to the new changelog file.
- **Add the performance graphs** to the release note.

Add to git
::::::::::

.. code-block:: shell

    poetry run make preqa
    git add docs/reference
    git add -p

Run the full test suite
:::::::::::::::::::::::

.. todo::

    - This should be done from a clean virtualenv, but it's not yet the case (mitigated for now by using a clean git
      worktree on each release, but this is undocumented for now).

Git add is there to check nothing was modified by QA suite.

.. code-block:: shell

   poetry run make qa
   git add -p

Create the git release
::::::::::::::::::::::

.. code-block:: shell

    git commit -m "release: $VERSION"

Tag and push
::::::::::::

.. code-block:: shell

    git tag -am "release: $VERSION" $VERSION

.. code-block:: shell

    git push origin `git rev-parse --abbrev-ref HEAD` --tags


Eventually forward-port the new version
:::::::::::::::::::::::::::::::::::::::

If a newer version line is available, checkout and merge the new version into it.


Create the GitHub release
:::::::::::::::::::::::::

.. code:: shell

    open https://github.com/msqd/harp/releases/tag/$VERSION

Create the release from tag (button on the right).

To generate the markdown changes for github, use:

.. code-block:: shell

    pandoc -s -o changes.md docs/changelogs/$VERSION.rst

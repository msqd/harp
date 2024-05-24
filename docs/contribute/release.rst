Releasing
=========

.. warning::

    This guide is intended for release managers. If you're not trying to release a new harp version, then this is most
    probably not what you're looking for.

Prior to release
::::::::::::::::

1. Update and cleanup dependencies

- Read the dependencies description and ensure nothing is there while not used.

  .. code-block:: shell-session

      poetry show
      poetry show --tree

  .. code-block:: shell-session

      cd harp_apps/dashboard/frontend
      pnpm list


- Dashboard's frontend dependencies

  .. code-block:: shell-session

      (
           cd harp_apps/dashboard/frontend;
           pnpm update --interactive
      )

- Python dependencies

  .. code-block:: shell-session

      poetry up

- Check that all tests are passing (they need background services, for now)

  .. code-block:: shell-session

      docker compose up -d
      poetry run make qa

- Eventually commit the updated dependencies

  .. code-block:: shell-session

    git add -p pyproject.toml poetry.lock harp_apps/dashboard/frontend/package.json harp_apps/dashboard/frontend/pnpm-lock.yaml
    git commit -m "chore: cleanup and update dependencies"
    git push


Releasing a new version
:::::::::::::::::::::::

1. Pull and check dependencies are there.

.. code-block:: shell-session

    git pull --tags
    make install-dev

2. Generate next version number

.. code-block:: shell-session

    poetry version <patch|minor|major|prepatch|preminor|premajor|prerelease>
    # ... or edit the version in pyproject.toml

.. code-block:: shell-session

    export VERSION=`poetry version --short`
    export OLD_VERSION=`git describe --tags --abbrev=0`
    echo New version: $VERSION - Old version: $OLD_VERSION

3. Update version numbers in other project files...

.. code-block:: shell-session

    gsed -i -e "s/^__version__ = .*/__version__ = \"$VERSION\"/" harp/__init__.py
    gsed -i -e "s/^appVersion: .*/appVersion: \"$VERSION\"/" misc/helm/charts/harp-proxy/Chart.yaml

4. Generate a changelog...

.. code-block:: shell-session

    git log --oneline --no-merges --pretty=format:"* %s (%an)" $OLD_VERSION.. > docs/contribute/changelogs/$VERSION.rst
    git add docs/contribute/changelogs/$VERSION.rst

5. Reboot computer and un the benchmarks on new version

.. code-block:: shell-session

    docker-compose up -d
    poetry run make benchmark-save

.. todo:: use poetry version for benchmark save ?

- Edit the **changelog index** (`docs/contribute/changelogs/index.rst`) to add the new version (title, date).
- Add a **title** to the new changelog file.
- Add the **performance graphs** to the release note.

6. Add to git

.. code-block:: shell-session

    poetry run make preqa
    git add docs/reference
    git add -p

7. Run a full test suite again (todo: from a clean virtualenv)

.. todo::

    - This should be done from a clean virtualenv, but it's not yet the case.
    - Interface snapshots should be run in a repeatable environment (docker ?).

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

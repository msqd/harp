Release notes
=============

Prior to release
::::::::::::::::

* dependency cleanup (remove unused dependencies, update ...)

Releasing a new version
:::::::::::::::::::::::

Considering the main project repository is setup as "upstream" remote for git...

1. Pull and check dependencies are there.

.. code-block:: shell-session

    git pull upstream `git rev-parse --abbrev-ref HEAD`
    git fetch upstream --tags
    pip install -U pip wheel twine git-semver
    poetry lock

2. Generate next version number

.. todo::

    Use `poetry version` to bump ?

.. code-block:: shell-session

    # Generate patch level version (x.y.z -> x.y.z+1)
    NEXT_VERSION=`git semver --next-patch`
    echo $NEXT_VERSION

    # Generate minor level version (x.y.z -> x.y+1.0)
    NEXT_VERSION=`git semver --next-minor`
    echo $NEXT_VERSION

    # Generate major level version (x.y.z -> x+1.0.0)
    NEXT_VERSION=`git semver --next-major`
    echo $NEXT_VERSION

Update version numbers in `pyproject.toml` and `harp/__init__.py`...

.. code-block:: shell-session

    gsed -i -e "s/^version = .*/version = \"$NEXT_VERSION\"/" pyproject.toml
    gsed -i -e "s/^__version__ = .*/__version__ = \"$NEXT_VERSION\"/" harp/__init__.py
    gsed -i -e "s/^appVersion: .*/appVersion: \"$NEXT_VERSION\"/" misc/helm/charts/harp-proxy/Chart.yaml

Generate a changelog...

.. code-block:: shell-session

    git log --oneline --no-merges --pretty=format:"* %s (%an)" `git tag | tail -n 1`.. > docs/development/changelogs/$NEXT_VERSION.rst
    git add docs/development/changelogs/$NEXT_VERSION.rst


.. code-block:: shell-session

    docker-compose up -d
    poetry run make benchmark-save

Then **edit the changelogs index** to add a title, date, **run the benchmarks** and **add perf graphs to docs**.

Add to git ...

.. code-block:: shell-session

    git add -p pyproject.toml poetry.lock harp/__init__.py add docs/development/changelogs/
    poetry run make preqa; git add docs/reference; git add -p

3. Run a full test suite (todo: from a clean virtualenv)

.. todo::

    - This should be done from a clean virtualenv, but it's not yet the case.
    - Interface snapshots should be run in a repeatable environment (docker ?).

.. code-block:: shell

   poetry run make qa

**TODO: Generate benchmarks ???**

4. Create the git release

.. code-block:: shell

    git commit -m "release: $(poetry version)"

Then when commit succeeds ...

.. code-block:: shell

    git tag -am "$(poetry version)" $(poetry version --short)
    git push origin `git rev-parse --abbrev-ref HEAD` --tags
    git push upstream `git rev-parse --abbrev-ref HEAD` --tags

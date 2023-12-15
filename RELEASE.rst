How to make a release?
======================

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

    git log --oneline --no-merges --pretty=format:"* %s (%an)" `git tag | tail -n 1`.. > docs/changelogs/$NEXT_VERSION.rst
    git add docs/changelogs/$NEXT_VERSION.rst

Then **edit the changelogs index** to add a title and a date.

Add to git ...

.. code-block:: shell-session

    git add -p pyproject.toml poetry.lock harp/__init__.py
    make preqa; git add docs/reference; git add -p

3. Run a full test suite (todo: from a clean virtualenv)

.. todo::

    - This should be done from a clean virtualenv, but it's not yet the case.
    - Interface snapshots should be run in a repeatable environment (docker ?).

.. code-block:: shell

   make qa

4. Create the git release

.. code-block:: shell

    git commit -m "release: $(poetry version)"
    git tag -am "$(poetry version)" $(poetry version --short)

    # Push to origin
    git push origin `git rev-parse --abbrev-ref HEAD` --tags
    git push upstream `git rev-parse --abbrev-ref HEAD` --tags


5. (open-source) Create the distribution in a sandbox directory & upload to PyPI (multi python versions).

.. code-block:: shell

    (VERSION=`python setup.py --version`; rm -rf .release; mkdir .release; git archive `git rev-parse $VERSION` | tar xf - -C .release; cd .release/; for v in 3.6 3.7 3.8 3.9; do pip$v install -U wheel; python$v setup.py sdist bdist_egg bdist_wheel; done; twine upload dist/*-`python setup.py --version`*)

And maybe, test that the release is now installable...

.. code-block:: shell

    (name=`python setup.py --name`; for v in 3.6 3.7 3.8 3.9; do python$v -m pip install -U virtualenv; python$v -m virtualenv -p python$v .rtest$v; cd .rtest$v; bin/pip --no-cache-dir install $name; bin/python -c "import $name; print($name.__name__, $name.__version__);"; cd ..; rm -rf .rtest$v; done; )

Note that for PRERELEASES, you must add `--pre` to `pip install` arguments.

.. code-block:: shell

    (name=`python setup.py --name`; for v in 3.6 3.7 3.8 3.9; do python$v -m pip install -U virtualenv; python$v -m virtualenv -p python$v .rtest$v; cd .rtest$v; bin/pip --no-cache-dir install --pre $name; bin/python -c "import $name; print($name.__name__, $name.__version__);"; cd ..; rm -rf .rtest$v; done; )

Setting Up PyPI Trusted Publishing
===================================

Trusted Publishing is the secure, modern way to publish Python packages to PyPI without needing API tokens.
It uses OpenID Connect (OIDC) to allow GitHub Actions to authenticate directly with PyPI.

Benefits
::::::::

* **No API tokens to manage** - PyPI generates short-lived tokens automatically
* **More secure** - Tokens are scoped to specific workflows and expire immediately
* **Simpler setup** - No secrets to configure in GitHub

Prerequisites
:::::::::::::

* Admin access to the PyPI project (or create a new project)
* Admin access to the GitHub repository

Setup Steps
:::::::::::

1. Configure TestPyPI (for testing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, set up TestPyPI to test your workflow safely:

a. Go to https://test.pypi.org/manage/account/publishing/
b. Click "Add a new publisher"
c. Fill in the details:

   * **PyPI Project Name**: ``harp-proxy``
   * **Owner**: ``msqd`` (your GitHub organization/username)
   * **Repository name**: ``harp``
   * **Workflow name**: ``release.yml``
   * **Environment name**: ``testpypi``

d. Click "Add"

2. Configure Production PyPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once testing is successful, configure production PyPI:

a. Go to https://pypi.org/manage/account/publishing/
b. Click "Add a new publisher"
c. Fill in the details:

   * **PyPI Project Name**: ``harp-proxy``
   * **Owner**: ``msqd``
   * **Repository name**: ``harp``
   * **Workflow name**: ``release.yml``
   * **Environment name**: ``pypi``

d. Click "Add"

3. Set up GitHub Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure manual approval for production releases:

a. Go to your GitHub repository → Settings → Environments
b. Create two environments:

   **testpypi** (automatic):

   * Name: ``testpypi``
   * No protection rules needed (publishes automatically for testing)

   **pypi** (manual approval):

   * Name: ``pypi``
   * Enable "Required reviewers"
   * Add yourself (and other maintainers) as required reviewers
   * This ensures someone must approve before publishing to production PyPI

Testing the Setup
:::::::::::::::::

To test the release workflow:

.. code-block:: shell

    # Create a test tag (use -rc suffix to mark as pre-release)
    git tag 0.9.0-rc1
    git push origin 0.9.0-rc1

This will:

1. Build the wheel automatically
2. Test it in a container
3. Publish to TestPyPI (automatic)
4. Wait for manual approval before publishing to PyPI
5. Create a GitHub release after PyPI publication

Check the results:

* GitHub Actions: https://github.com/msqd/harp/actions
* TestPyPI: https://test.pypi.org/project/harp-proxy/
* PyPI: https://pypi.org/project/harp-proxy/ (after approval)

Releasing for Real
::::::::::::::::::

Once you've verified everything works with a test tag:

.. code-block:: shell

    # Create the actual release tag
    git tag 0.9.0
    git push origin 0.9.0

Then:

1. Watch the GitHub Actions workflow progress
2. When it reaches the PyPI publishing step, you'll get a notification
3. Review the TestPyPI release
4. Approve the deployment to production PyPI
5. The GitHub release will be created automatically

Troubleshooting
:::::::::::::::

**Error: "Trusted publishing exchange failure"**

This means the PyPI trusted publisher configuration doesn't match your workflow.
Double-check:

* Project name is exactly ``harp-proxy``
* Workflow name is exactly ``release.yml``
* Environment name matches (``pypi`` or ``testpypi``)
* Repository owner and name are correct

**Error: "Permission denied"**

Make sure the workflow has the required permissions:

.. code-block:: yaml

    permissions:
      id-token: write  # Required for trusted publishing

**TestPyPI worked but PyPI failed**

Make sure you configured the PyPI trusted publisher separately (it's a different website).

Maintenance
:::::::::::

* No API tokens to rotate or expire
* If you rename the workflow file, update the trusted publisher configuration on PyPI
* If you change the GitHub organization/repository, reconfigure trusted publishing

References
::::::::::

* `PyPI Trusted Publishing Guide <https://docs.pypi.org/trusted-publishers/>`_
* `GitHub Actions Publishing Guide <https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>`_

Branching
=========

We use various git branches for development.

Version-line branches
:::::::::::::::::::::

The version-line branches contains the latest code for a given version line. For example, the `0.6` branch contains the
latest code for the `0.6.x` version line, etc. We keep the version line branches open while a version is considered
active, after which we remove the branch.

Version tags
::::::::::::

Each released version has a matching tag, and even old unmaintained version will keep their tags for historical
purposes.

Feature branches
::::::::::::::::

Each feature is developmed into its own branch, and merged into the version-line branch when ready. This can be done
using github pull requests.

Docker tags
:::::::::::

Docker images are published for each tag, and for version-line branches. For example, the `0.6` branch will have a
corresponding docker image (git-0.6), as well as the `0.6.0a1` tag.

We plan in the future to also publish docker tags for version lines that does not follow git version-line branch but the
latest stable version in the version line.

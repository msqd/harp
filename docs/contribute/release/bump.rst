Bumping versions
================

When a new «line» of development is started, a few housekeeping tasks are required.

* create the new line branch in git
* add the line to readthedocs
* grep and update the hardcoded versions in the new line (readme, helm chart, ...)

Change main line
::::::::::::::::

This happens when a new version is being released. For example, I'm writing this while we're moving from the 0.7 line to
the 0.8 line. No need to wait for the actual release to start this process, as long as it happens in the next few days.

* change the default branch on github
* change the default branch in gitlab
* update readthedocs

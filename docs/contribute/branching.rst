Branching
=========

Why this model, and what was rejected: `ADR-0004 <https://github.com/msqd/harp/blob/main/docs/adr/0004-trunk-main-and-version-line-branches.md>`_.

Branches
::::::::

``main``
    The default branch, where the next version is built. It never changes. Every pull request targets
    ``main``, except a backport.

Version line ``X.Y``
    A branch created on the ``X.Y.0`` tag when that release ships (``0.10`` holds ``0.10.x``). It moves
    only through backports, freezes once ``X.Y+1.0`` ships, and is never deleted: its documentation and
    the Help links of installations still running it depend on it.

Work branch
    One per issue, named ``<type>/<issue>-<slug>`` (``fix/1046-system-config-set-equals``), merged
    through a pull request.

``main`` and every version line are protected: a pull request and a green *All Checks Passed* are
required, for administrators too, and force-push and deletion are refused.

Versions
::::::::

- A release is an annotated tag ``X.Y.Z`` (pre-releases ``X.Y.Z-alphaN``, ``X.Y.Z-rcN``), cut per
  :doc:`release/python`.
- Right after ``X.Y.0`` is tagged, ``main`` moves to ``X.Y+1.0.dev0``. A build from ``main`` therefore
  reports a development version.

Patch releases and backports
::::::::::::::::::::::::::::

Only the latest version line receives patch releases, for bugs and security fixes, never features. The
product owner proposes a patch release and the user decides it.

A fix lands on ``main`` first, through a normal pull request. A second pull request, targeting ``X.Y``,
cherry-picks it with ``git cherry-pick -x <sha>`` so the commit names its origin. A fix that no longer
applies to ``main`` goes to ``X.Y`` directly, and its pull request says why.

Documentation versions
::::::::::::::::::::::

========================  ==========================  =============================================
Read the Docs slug        Built from                  Warning shown
========================  ==========================  =============================================
``latest``                ``main``                    development version, unreleased
``stable``                the highest release tag     none
``X.Y``                   the ``X.Y`` branch          not the stable version
========================  ==========================  =============================================

Each version titles itself ``HARP Proxy X.Y (role)``, the role computed at build time from the version
built and the release tags (never from the Read the Docs name):

- ``next``: unreleased, ahead of the highest release tag (``latest``, ``0.12 (next)``).
- ``stable``: the line of the highest release tag, built as ``stable`` or as its ``X.Y`` branch.
- ``oldstable``: the line before it.
- older lines show only ``X.Y``.

"Edit on GitHub" opens ``main`` on ``latest`` and the ``X.Y`` branch elsewhere. A local build titles
itself from the package version. A line only changes role when it is rebuilt: see
:doc:`release/python`, step 10.

The warnings are Read the Docs' own (Addons, version warning), not part of our build. The dashboard's
Help link opens ``/en/X.Y/`` for a release and ``/en/latest/`` for a development build.

Docker images
:::::::::::::

- A push to ``main`` publishes ``unstable``.
- A push to a version line ``X.Y`` publishes ``X.Y-git``.
- A release tag ``X.Y.Z`` publishes ``X.Y.Z``, ``X.Y`` and ``X`` (and ``latest`` on Docker Hub); a pre-release
  tag publishes only itself.

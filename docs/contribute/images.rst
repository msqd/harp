Captures and diagrams
=====================

Images in the README and in the docs are generated, so they follow the product instead of drifting from it. Nothing
here is edited in a graphics tool.

Dashboard captures
------------------

.. code-block:: shell

    make docs-assets

This runs ``python -m docs._captures``. It migrates a throwaway SQLite database, fills it with the fixed data of
``docs/_captures/seed.py``, serves the real dashboard on it with the clock frozen, and takes the screenshots with
Playwright (the one of the dashboard frontend, so ``make install-frontend`` and ``pnpm exec playwright install
chromium`` are the only prerequisites). The captures land in ``docs/user/images``. The viewport, the theme (light), the
clock and the data are fixed: running it again without a UI change gives the same files, byte for byte.

To capture another page, add an entry to ``shots`` in ``docs/_captures/capture.mjs``. To change what the dashboard shows,
edit the seed; keep it derived from constants and the seeded random generator, never from the current time.

Diagrams
--------

Diagrams are `Graphviz <https://graphviz.org/doc/info/lang.html>`_ text sources in ``docs/images/diagrams/*.dot``. The
docs render them at build time with the ``graphviz`` directive, which needs the ``dot`` executable (``apt install
graphviz``, ``brew install graphviz``; Read the Docs installs it):

.. code-block:: rst

    .. graphviz:: ../images/diagrams/how-it-works-overview.dot

The README is plain reStructuredText that GitHub and PyPI render, so it links the SVG files rendered next to the
sources. ``make docs-assets`` renders them too, or only them with ``uv run python -m docs._captures diagrams``. Commit the
``.dot`` and the ``.svg`` together.

.. graphviz:: ../images/diagrams/how-it-works-overview.dot

Class diagrams, such as the event hierarchies in :doc:`/core/events`, have no source file: they are derived from the
code with the ``inheritance-diagram`` directive.

The choices behind this, and the options rejected, are in `ADR-0006
<https://github.com/msqd/harp/blob/main/docs/adr/0006-generated-captures-and-text-diagrams.md>`_.

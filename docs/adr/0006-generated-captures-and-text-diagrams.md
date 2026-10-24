# ADR-0006: Captures come from a seeded HARP through Playwright; diagrams are Graphviz text

- **Status**: draft
- **Date**: 2026-10-24
- **Decided in**: [#1440](https://github.com/msqd/harp/issues/1440)

Dashboard captures are produced by one command that seeds a throwaway SQLite database with fixed
transactions, serves the real dashboard on it with the clock frozen, and screenshots it with Playwright at
a fixed viewport in the light theme. Diagrams are Graphviz `.dot` text in `docs/images/diagrams/`:
Sphinx renders them at docs build, and the same command renders the SVGs the README links to. Class
diagrams of the event hierarchies use `sphinx.ext.inheritance_diagram`, so they are derived from the code.

## What was actually being decided

README and docs images are hand-made, outside the repo, and date from 2024. Nobody can refresh them
without a graphics tool, so they drift. The README cannot run Sphinx (GitHub and PyPI render it as plain
reStructuredText), so whatever it shows must be a file the repository holds.

## Capture tool

Playwright, from the dashboard frontend. It is already a dependency, its browsers are already installed
by the frontend tests, and it controls viewport, color scheme and clock. A real seeded HARP is used rather
than the dashboard's MSW mocks: the mocks are hand-written API payloads that can drift from the backend,
and a capture of them would show what the mocks say, not what the product does.

Determinism comes from fixed transaction ids and timestamps in the seed, a frozen server clock (the
overview buckets by `now`), `page.clock` in the browser, fixed ports and a fixed hash seed (the dashboard lists
facet values in set order), a pinned version string, and animations and GPU rasterization disabled.

### Rejected

- **MSW mocks as the data source.** Simpler, no backend, but can lie about the product.
- **Python Playwright.** A second install of the same tool, and a second set of browsers.
- **Hand-taken screenshots, documented procedure.** The status quo; it is what drifted.
- **Visual-regression snapshots in CI.** Different goal: it would fail builds on pixel noise. A re-run
  must be stable, but committing new captures stays a deliberate act.

## Diagram format

Graphviz. `sphinx.ext.graphviz` is already enabled, Read the Docs already installs `graphviz`, and
`docs/apps/proxy/settings.dot` already uses it. No new dependency.

### Rejected

- **Mermaid.** GitHub renders it natively in Markdown, but not in the reStructuredText README, and Sphinx
  needs a third-party extension and a browser or Node toolchain to render at build.
- **D2.** Nicer output, but a Go binary to install in every docs environment, and an extension to maintain.
- **Excalidraw or other editors, exported as PNG.** What exists today: not diffable, not reviewable.

## Consequences

- The README overview diagrams are SVG files rendered by the command and committed; the docs render the
  same `.dot` sources at build. Both renderers are Graphviz, so they differ at most by version.
- Graphviz output shifts slightly between versions: regenerate, and commit, with a recent one.
- The hand-drawn look (icons, shadows) of the current README drawings is lost in favor of plain boxes.
- The dependencies capture lists the packages of the environment it runs in: it changes with the lockfile, and
  its order follows the filesystem.
- #892 reuses the capture command for the redesigned dashboard user guide.

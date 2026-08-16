What the gate does not run
==========================

.. note::

    Written for the next release manager. It assumes none of the context of the release it came
    from, and it exists to answer one question: what does a green gate on this project mean, and
    what does it not mean?

    The numbers are from the 0.10 cut, measured at ``d5323a6d``. Treat them as a worked example.
    Re-measure before your own cut, because the point of this document is the method, not the
    figures.


The thesis, in one example
:::::::::::::::::::::::::

Under the default test matrix, HARP's MySQL tests are not red. They are **absent**.

.. code-block:: shell-session

    $ uv run pytest harp_apps/storage -k mysql -q --collect-only
    1/101 tests collected (100 deselected)

The one test that collects compiles SQL and never opens a connection. ``make qa`` does not fail on
MySQL. It silently has no MySQL, and reports success.

That is not a broken test or a failing gate. It is a whole supported backend quietly not present in
the run, counted as a pass. Everything else in this document is a variation on it.

**A backend that fails loudly gets fixed. A backend that is never collected gets counted as
passing.**


Theme one: the gates report what they decided to do, not what they observed
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

``make test`` decided it had run the frontend. ``make qa-full`` decided the backend result was the
whole result. ``bin/build_wheel`` decided an absent ``unzip`` meant absent assets.
``misc/cache-tests/run-tests.sh`` decided that writing a file was the same as reading it.

In each case the number printed at the end was true about the runner's intentions and silent about
reality. Three report success without observing the result. One reports failure without observing
it. Same root, opposite signs, and the pair makes the point better than either alone: **the gate
does not distinguish between what it measured and what it assumed.**


Theme two: a measurement can mean something other than what it appears to say
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

Five times during one release, on five different tools, output was taken at face value and meant
something else.

.. list-table::
    :header-rows: 1
    :widths: 30 33 37

    * - The output
      - Read as
      - Actually
    * - ``unzip`` absent, stderr discarded
      - frontend assets missing from the wheel
      - the tool was missing; the wheel held all 32
    * - a warning attributed to an ``asyncmy`` test
      - asyncmy has a teardown defect
      - a garbage collector finalizer, attributed to whatever ran when the collector woke
    * - ``FakeDatetime`` rejected by MariaDB
      - HARP cannot write transactions on MariaDB
      - freezegun's test double, never constructed in production
    * - the first screen of a failure list
      - the failure list
      - 462 errors, only countable with ``grep -c``
    * - escape sequences in piped output
      - the CLI ignores that stdout is a pipe
      - ``FORCE_COLOR`` was set in the shell doing the measuring

Two rules follow.

**Attribution is not evidence.** A test runner will happily name a test that had nothing to do with
the failure. Any per-test count inherits that noise.

**A count omits what it did not do.** ``2480 passed`` is the same number whether the MySQL matrix
ran and passed or never existed.

The discipline that separated a release scare from a footnote in the MariaDB case was not
cleverness. It was reproducing the failure outside the harness that reported it, and finding that it
did not reproduce.

The last row is the one to read twice, because it is the one that got past everybody. The claim was
checked by a second person, who ran the same reproduction, on the same machine, in the same shell,
and confirmed it. **A verification that inherits the conditions of the thing it is verifying is not
a verification.** It has the shape of rigour and none of the content, and in this case it promoted a
wrong assertion into a user-facing report before anyone looked again.

So "reproduce it outside the harness" is broader than it first sounds. Outside pytest was enough for
the freezegun case. It was not enough here, because the harness was the shell. When you cannot
change machines, at least change the environment: ``env -i``, an unset of the variables you did not
choose, a different user.


The evidence
::::::::::::

Deliberately skipped
--------------------

.. list-table::
    :header-rows: 1
    :widths: 55 12 33

    * - What
      - Count
      - Reason recorded
    * - ``tests/test_uv_integration.py::TestUVIntegration``
      - 8
      - **none**
    * - ``test_application_filtering_integration.py``
      - 3
      - yes, "out of scope"
    * - ``@pytest.mark.xfail``
      - 4
      - per marker
    * - ``@pytest.mark.skipif``
      - 8
      - per marker
    * - ``pytest.skip()`` at runtime
      - 13
      - per call

``TestUVIntegration`` is why this category is worth writing down. Eight tests whose purpose is to
prove ``uv run harp-proxy``, ``uvx harp-proxy`` and ``python -m harp`` work, disabled by a bare
class-level ``@pytest.mark.skip`` with **no reason string**, in the release whose headline packaging
change was the migration to UV. They were born disabled in the commit that introduced UV and shipped
disabled through the release before.

Each method still carried ``@pytest.mark.skipif(not is_uv_available(), ...)``. Those guards became
dead code the moment the blanket skip landed on top, and nothing reported that they had stopped
meaning anything.

Run them and six of eight pass; the two failures were assertions about a command that had been
renamed. Everything the class was written to prove worked the whole time.

This is the **unknown** category, and it is the one this document exists for. For two releases the
honest answer to "why are these off" was that nobody knew, and nothing in the repository asked.

Deselected by marker
--------------------

All three CI backend jobs run ``-m 'not subprocess'``, excluding **35 tests** from every CI run: 27
cookiecutter integration tests and the 8 above, which are therefore excluded twice. Removing either
lock alone would have changed nothing.

``make qa`` does not filter, so **the release manager is the only person who ever meets them**. At
the 0.10 cut all 24 failing ones shared a single cause, documented in :doc:`chores`: the generated
project pins ``harp-proxy>=X.Y.Z`` and PEP 440 excludes pre-releases, so nothing resolves until the
version is published.

Dead at fixture setup
---------------------

**462 errors, one cause, and no MySQL or MariaDB test body had ever executed on any release.**

Every MySQL parametrisation died in ``harp_apps/storage/conftest.py`` with ``ModuleNotFoundError: No
module named 'MySQLdb'`` before its body ran. 474 of 499 non-passing results were that one thing.

An error count that dwarfs the failure count is almost always one problem wearing many hats. Check
that before reading anything else into the numbers.

Two stacked defects, neither sufficient alone: the test URL builder rewrote a string format that
testcontainers had changed in a version inside our own dependency range, so the driver never reached
the URL; and the ``mysql`` dependency group was never synced, so no driver was installed either. A
consequence worth noticing on its own: because the driver never reached the URL, the two driver legs
of the matrix produced an identical connection string, so one of them had never been executed by
anything while appearing in every test id.

Repaired locally, the suite ran and **HARP worked on MySQL and MariaDB**, including the full-text
search path that a fix in that release had repaired and that no gate had ever executed.

Never reached
-------------

**The frontend, whenever the backend fails.** ``make test`` runs ``test-backend`` first, and a
failure stops ``make`` before ``test-frontend``. On the ``qa-full`` run no frontend suite ran at
all: not "ran and failed", not reported as skipped, absent, with nothing in the log saying so.

**Every RFC 9111 cache test.** ``make test-e2e-cache`` starts its origin server, then HARP fails to
boot because ``misc/cache-tests/config.yml`` hardcodes a PostgreSQL URL that nothing provisions. The
suite ends having executed nothing. The credentials in that file are transposed between username and
password, which dates the last successful run: a typo like that cannot survive one.

In no gate at all
-----------------

.. list-table::
    :header-rows: 1
    :widths: 40 30 30

    * - Suite
      - Where it lives
      - Where it runs
    * - ``make qa-full`` (all databases)
      - Makefile
      - nowhere; ``TEST_ALL_DATABASES`` defaults false
    * - ``-m subprocess`` (35 tests)
      - pytest marker
      - nowhere
    * - ``make test-e2e-cache`` (RFC 9111)
      - Makefile
      - nowhere
    * - ``pnpm test:browser``
      - package.json
      - nowhere
    * - visual suite ``test:ui:dev``
      - ``make test-frontend``
      - not in CI
    * - ``pnpm lint``
      - package.json
      - nowhere

CI runs three backend jobs, ``pnpm test:unit``, and a documentation build. That is the entire
automated gate. Everything else in the Makefile runs only when a human runs it.

Observed but not reported
-------------------------

**Success reported without observing the result.** ``make qa`` converts a frontend failure into the
word ``Skipped.`` and a green exit, because ``... && $(MAKE) test-frontend || echo "Skipped."``
cannot tell a deliberate skip from a failure. ``make test-e2e-cache`` writes its RFC 9111 results to
a JSON file that nothing reads. The second is worse than the first: a swallowed failure at least
leaves a number on screen to scroll back to, while a file nobody opens leaves nothing at all.

**Failure reported without observing the result**, the mirror. ``bin/build_wheel`` counted wheel
assets by shelling to ``unzip`` and discarding its stderr, so a missing tool was indistinguishable
from an empty archive. The build died with "frontend assets were not included in the wheel" while
the wheel held all 32. A check whose failure mode impersonates the condition it guards is worse than
no check, and this one fired at the exact moment someone was cutting a release.

Unknown
-------

Kept deliberately, because the temptation to drop an entry once its alarming version turns out to be
wrong is itself the failure mode this document is about.

Three consoles in the codebase are constructed with ``force_terminal=True``. Whether that produces
styled output in a pipe for any command a user would pipe is **not known**. The commands that could
be exercised were clean once ``FORCE_COLOR`` was unset, so there is no evidence of a user-visible
problem, and no evidence there is not one.

Audit a migration's diff for what it turned off
-----------------------------------------------

**A large migration is where suppressions get introduced under pressure, so its diff is worth
reading separately for what it silenced rather than for what it changed.**

Two of the entries above turned out to come from the same commit, the migration from Poetry to UV.
That was enough of a coincidence to go and read the whole diff. It had silenced five things, none of
them with a recorded reason, and all five were still in place two releases later:

#. ``@pytest.mark.skip`` on the ``TestUVIntegration`` class, eight tests, no reason string.
#. ``-$(UV_RUN) pre-commit`` in ``preqa``, whose ``-`` makes ``make`` ignore the exit status.
#. ``continue-on-error: true`` on the **Build Documentation** CI job.
#. ``continue-on-error: true`` on the **Build Storybook** CI job.
#. The entire ``test-frontend-visual`` CI job commented out, including the visual suite.

The pattern is ordinary and forgivable: someone migrating a build system meets a wall of unrelated
failures, silences them to get the migration through, intends to come back, and does not. It cost
two releases and a full day of investigation to rediscover two of them from their symptoms. Reading
one diff found the other three in minutes.

Both ``continue-on-error`` jobs currently pass, so those two are dormant rather than actively hiding
a failure. That is worth stating precisely: dormant is not the same as harmless, because the whole
point of the flag is that the day one of them does fail, nothing will say so.

The search is cheap and bounded. In the diff of any large migration, look for ``skip``, ``xfail``,
``continue-on-error``, ``|| true``, ``|| echo``, ``--no-verify``, ``noqa``, leading ``-`` on make
recipes, new ``exclude`` entries in tool configuration, and commented-out jobs or steps.


What to do with this at your cut
::::::::::::::::::::::::::::::::

Every entry here was invisible for the same reason: **the runner prints a number that omits what it
did not do.** A gate that printed

.. code-block:: text

    35 selected, 8 unconditionally skipped, 462 fixture errors,
    2 driver legs identical, frontend not reached

would have surfaced all of it without anyone writing a single new test.

Until a gate prints that by itself, do it by hand. Before the tag:

#. **Read the suites' summary lines, not the exit code.** See :doc:`chores` for the specific traps.
#. **Count what was not run**, not only what failed. Skips, deselections, and collection counts.
#. **Ask what an error count means** when it dwarfs the failure count. It is usually one fixture.
#. **Check that each suite you believe in actually executed.** A suite that cannot start reports
   nothing, and nothing looks like success.
#. **Re-measure this document.** If a number here has changed, that change is itself the finding.

Read the categories in this order, because it is the order in which they hide things:

#. **Unknown**, where a real defect sits looking like an accepted one.
#. **Absent**, where nothing was collected and the count says nothing.
#. **Dead at fixture setup**, where one problem wears many hats.
#. **Never reached**, which leaves no trace in the output at all.

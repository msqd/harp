Validation and sign-off
=======================

.. important::

    **A release is not tagged until the user has signed off.** If you are cutting a release and
    nobody has told you the sign-off happened, you are not ready to cut. Stop and ask.

Cutting a release is the last step of a sequence, not the first. This page describes the sequence,
because :doc:`python` describes only the mechanics and a reader working through it end to end would
otherwise never be told to wait for anyone.


The gate
--------

.. list-table::
    :header-rows: 1
    :widths: 5 45 25

    * - #
      - What happens
      - Who owns it
    * - 1
      - The decision to cut this release.
      - The user
    * - 2
      - The recette.
      - The product owner
    * - 3
      - Sign-off on all elements, including their own manual pass.
      - The user
    * - 4
      - The cut: version, date, tag, push.
      - A software engineer

The order is the point. Step 4 does not begin until step 3 has happened.


1. The decision is the user's
:::::::::::::::::::::::::::::

The user decides that a release is to be cut, and a software engineer performs it. Neither the
product owner nor the engineer starts a cut on their own initiative.


2. The recette belongs to the product owner
:::::::::::::::::::::::::::::::::::::::::::

It is not delegated to the engineer who wrote the code. It has four parts:

- run every test that can be run;
- test and challenge every changelog entry against the code and the running product;
- build a testing environment for the user, ready to use;
- deliver a *cahier de recette*, a manual test plan the user executes on their side.

The reason it is not delegated is the reason this project applies everywhere else: **a green result
from the person who wrote the thing carries no information**, because they already believed it. The
product owner accepted the work, so they verify the whole of it before the user is asked to.

The contents of the recette are the product owner's to define. Nothing here constrains them.


3. The user signs off
:::::::::::::::::::::

The user's manual pass is **part of** the recette, not a formality after it. It exists because some
defects are only visible to somebody using the product rather than testing it.

Sign-off covers all elements, not just the manual pass.


4. Then the cut
:::::::::::::::

A software engineer performs it, following :doc:`python`. The version number and the release date
are set at that moment and not before.


If you are the release manager
------------------------------

You are step 4. Two things follow:

- **Do not tag on your own judgement**, however green everything looks. A passing test suite is not
  a sign-off, and neither is an empty pull-request queue.
- **If you inherited this release mid-flight**, from a lost session, a handover or a colleague,
  assume the sign-off has *not* happened until somebody tells you it has. Ask. The cost of asking is
  a message; the cost of assuming is a published version that cannot be unpublished.

See :doc:`what-the-gate-does-not-run` for why a green ``make qa`` is a weaker statement than it
looks, which is a large part of why steps 2 and 3 exist at all.

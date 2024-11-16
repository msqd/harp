Contributors
============

Updating the contributors list contains a bit of a manual process.

Check missing contributors:

.. code:: shell

    all-contributors check

Add a new contributor (see https://allcontributors.org/docs/en/emoji-key for reference):

.. code:: shell

    all-contributors add <username> <contributions>

Regenerate the contributors list:

.. code:: shell

    all-contributors generate

Then, copy the generated list html from ``CONTRIBUTORS.md`` to the ``README.rst`` file,
with proper indentation in ``.. raw:: html`` block, along with the badge at the top.

Contributors
============

People & Credits in the README is generated from ``.all-contributorsrc``. It is brought up to date
before every minor release (see :doc:`chores`).

Who is credited
:::::::::::::::

Every person, never a bot, who:

* authored a merged commit or pull request (``code``, ``doc``, ``test``, ``example``...);
* opened an issue (``bug`` for a defect, ``ideas`` for a request or a design discussion);
* reported a vulnerability and accepted the credit on its published security advisory
  (``security``). Leave out a reporter who has not accepted it.

See https://allcontributors.org/docs/en/emoji-key for the types.

Find who is missing
:::::::::::::::::::

``all-contributors check`` only compares commit authors. Also list issue and pull request authors,
and the credits of published advisories:

.. code:: shell

    all-contributors check
    gh api --paginate 'repos/msqd/harp/issues?state=all&per_page=100' --jq '.[].user.login' | sort -u
    gh api 'repos/msqd/harp/security-advisories?state=published' \
        --jq '.[].credits_detailed[] | select(.state == "accepted") | .user.login'

Update the list
:::::::::::::::

Add each missing contributor, or a new type to an existing one:

.. code:: shell

    all-contributors add <username> <contributions>

Regenerate the list:

.. code:: shell

    all-contributors generate

Then, copy the generated list html from ``CONTRIBUTORS.md`` to the ``README.rst`` file,
with proper indentation in ``.. raw:: html`` block, along with the badge at the top.

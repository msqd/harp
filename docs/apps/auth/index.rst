Auth
====

.. tags:: applications

.. versionadded:: 0.13

The ``harp_apps.auth`` application owns who may use HARP: the **accounts**, how they **sign in** (a password, and the
**sessions** it opens), the **role** each one holds, and the **actor** a request stands for. The dashboard depends on
it, so it is loaded whenever a dashboard is.

.. toctree::
    :hidden:
    :maxdepth: 1

    Settings <settings>
    Internals </reference/apps/harp_apps.auth>


Accounts
::::::::

An account is something that signs in to HARP and holds a role: a person, or a machine. Accounts live in the
``auth_accounts`` table of the :doc:`storage </apps/storage/index>` database, which replaces the former ``users``
table. Favourites keep their author.

``username``
    Unique, up to 255 characters.

``display_name``
    Optional, shown in the dashboard header in place of the username.

``email``
    Optional and unique whatever the case: it is stored lower-cased. It is shown, and never a way in.

``kind``
    ``person``, ``machine`` or ``system``. ``anonymous``, the author of the favourites recorded before there were
    accounts, is a ``system`` account: no request is ever attributed to it, and a ``system`` account cannot sign in.

``role``
    ``viewer``, ``editor`` or ``admin``, see below.

``created_at``, ``last_seen_at``, ``disabled_at``
    ``last_seen_at`` is written at most once a minute. A disabled account answers ``401`` at its next request.

``disabled_reason``
    ``migrated`` on the accounts the migration disabled and the import has not enabled yet, ``operator`` once an
    Operator disabled one.

Accounts sign in with a **password** (see below), or with the deprecated **Basic** authentication of the dashboard
(:doc:`/apps/dashboard/settings`). The users declared there are **imported once** per database, at the first start with the ``auth`` application: a missing one
becomes an enabled ``admin`` person, one the migration disabled is enabled as ``admin``, and any other existing account
is left as it is, so a role or a disabling set with the commands below before that start wins. A ``system`` account
named ``basic-import`` records that it ran. Later starts import nothing: a configured user without an account, because
it was deleted, **or because it was added to ``dashboard.auth.users`` after the first import**, answers ``401``. Add
such a user with ``auth:create-account``. The role is the one of the account, read from
the database on every request: demoting or disabling an account applies at once.

Roles
:::::

Roles are ordered, each one includes what the one below it may do.

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - Role
      - May use
    * - ``viewer``
      - The overview, the transactions and their bodies, the metrics, and its own favourites.
    * - ``editor``
      - Also the topology, the storage state, and taking a remote endpoint up or down
        (``PUT /api/system/proxy``).
    * - ``admin``
      - Also the settings and the dependencies.

Every dashboard route declares the role it requires, and a request below it is answered ``403``. A route added
without a declared role is reserved to ``admin``. The dashboard shows the account and its role in its header, and
does not offer the pages the role cannot use.

There is no open mode: every request of the dashboard is resolved to an account, and ``dashboard.auth.type: none`` is
refused at start.


Signing in with a password
::::::::::::::::::::::::::

The password method needs no configuration: it is on when no sign-in method is configured (and next to Basic when
``dashboard.auth`` is). A person has one **identity** for it, a row of ``auth_identities`` keyed by ``password``, an
empty issuer and the username, holding the hash. ``/signin`` is the page, ``POST /api/auth/signin`` the request it makes.

**Passwords** are stored as Argon2id PHC strings (19 MiB, t=2, p=1) and hashed again at the next sign-in when these
parameters change. At most four verifications run at once. The policy is the one of NIST SP 800-63B-4: 15 to 256
characters, none from a bundled list of the 10 000 most common passwords, no composition rule and no expiry. An unknown
account, a disabled one and a wrong password are refused with the same answer, after the same verification.

**Failed sign-ins slow down, never lock out.** From the fifth failure on, for an account name and for an address, the
next attempt has to wait 1 second, then 2, 4, ... up to 5 minutes; an attempt made too early answers ``429`` with
``Retry-After`` and its password is not looked at. The count is kept for 15 minutes, in memory and per process. The
address is the one of the connection: ``X-Forwarded-For`` is not trusted, so behind a reverse proxy every visitor shares
the address of the proxy, and the per account wait is what protects an account.

**Sessions** are rows of ``auth_sessions``. The cookie holds a random 256 bits secret and nothing else (``HttpOnly``,
``SameSite=Lax``, ``Path=/``), and the table holds its SHA-256, so reading the database opens no session. Over HTTPS the
cookie is ``__Host-harp_session`` and ``Secure``; over plain HTTP it is ``harp_session``. A request is secure when the
reverse proxy says so (``X-Forwarded-Proto: https``) or when ``dashboard.public_url`` is an ``https`` URL, and only the
cookie of its flavour is read. The proxy strips both cookie names from the requests it forwards to an origin, and from
the responses it gets. A session ends after ``session_idle_hours`` (12) without a request or
after ``session_max_hours`` (168, 7 days) whatever the activity, both checked by the server at each request. Disabling
the account or lowering its role applies at the next request.

``POST /api/auth/signout`` ends the session of the request, ``POST /api/auth/signout-all`` every session of the account,
and ``POST /api/auth/password`` (``current``, ``new``) changes the password and ends the other sessions. Like every
state-changing route of the dashboard they only accept ``application/json`` from the dashboard itself, which is what
keeps a cross-site form out (:doc:`/apps/dashboard/index`). Same-origin hardening across ports is a separate change.


The setup link
::::::::::::::

While no enabled ``admin`` person exists, HARP logs a link at each start:

.. code-block:: text

    There is no administrator yet: ... http://localhost:4080/setup#<secret>

It names ``dashboard.public_url`` when set, else ``localhost`` and the dashboard port. Opening it asks for a username and
a password and creates the first Admin, already signed in. The secret is in the fragment of the URL, which a browser never
sends: it is in no access log and no ``Referer``. It is single use, valid ``setup_link_hours`` (72), stored as a SHA-256,
and replaced at each start while unused (so the one in the latest logs is the only one that works). A weak password or a
taken username leaves it valid for another try. It is void as soon as an Admin exists, however it came to exist.
**Until it is used the logs hold a secret that makes an administrator**: restrict who reads them.

Nothing configured with ``dashboard.auth`` needs it: the users declared there are imported as Admins, and no link is
logged.

The link is the minimal form of an **invitation**: a row of ``auth_invitations`` for the
``admin`` role with no ``invited_by``. Invitations for other accounts (#1523) use the same table and the same
acceptance, with an author, a role and an expected email set by an Admin: nothing here needs migrating, only the
acceptance generalising.


The actor
:::::::::

Resolving a request yields one **actor**: the account, the role the request acts with (the *effective* role), how it
got in (``via``, with ``via_id`` naming the credential) and the client acting on its behalf, if any. Controllers and
role checks read this and nothing else (:mod:`harp.security.actor`).

The effective role is the lowest of the role of the account and the cap of the credential. Basic has no cap, so for now
it is the role of the account.


Commands
::::::::

.. code-block:: shell

    harp-proxy auth:create-account alice --role editor --display-name "Alice" --email alice@example.com

creates an account with a password, which it asks for (twice, not shown; the policy above applies). ``--generate-password``
makes one up instead and shows it once. It is also the way back in when no Admin is left: create one, the role is read at
each request so there is nothing to restart. The command refuses a username (1 to 64 letters, digits or any of
``. _ @ + -``) or an email that is taken, and a database whose schema is not current.

.. code-block:: shell

    harp-proxy auth:set-role alice admin
    harp-proxy auth:disable-account alice
    harp-proxy auth:enable-account alice

change the role of an account, and revoke or restore it. **Revoke by disabling**: a disabled account answers ``401`` at
its next request and nothing is lost. Never delete a row: the favourites of the account go with it. These commands are
the way to manage accounts until the administration screen exists.


Upgrading
:::::::::

- **PostgreSQL**: the first revision of the ``auth`` branch renames ``users`` to ``auth_accounts``. The rows that
  existed become **disabled** ``viewer`` people, so nobody gets access from the migration; ``anonymous`` becomes an
  enabled ``viewer`` ``system`` account. The one-time import of the Basic users then enables the configured ones, as
  ``admin``. Enable any other with ``auth:enable-account`` and ``auth:set-role``.
  ``harp-proxy db:migrate down auth@base`` gives ``users`` back, which fails if a username is longer than 32
  characters. See :doc:`/operate/migrations`.
- **SQLite** is never migrated by alembic: a file written by an earlier version is refused at start, delete it (it is
  recreated) or run ``harp-proxy db:reset``.
- **MySQL and MariaDB** are deprecated and not migrated: the revision logs a warning and does nothing.


Loading
:::::::

The dashboard declares ``auth`` in its dependencies, so ``auth`` is loaded whenever the dashboard is, before it, even
when an ``applications:`` list does not name it (:doc:`/develop/run`). A HARP without dashboard loads no ``auth``.

Dashboard
=========

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.dashboard`` application implements the administrative api and micro-frontend.

If enabled, a server will be available (by default, on port `4080`) to access the :doc:`HARP Dashboard
</features/dashboard>` and observe whatever goes through the proxy.

It listens on ``dashboard.host``, which defaults to ``[::]`` (every interface) so a published Docker port keeps working.
Set ``host: 127.0.0.1`` to serve it on the loopback interface only. The startup warning about the dashboard login or
about disabled authentication names the address it listens on. ``dashboard.host`` applies to the dashboard port only,
not to ``metrics_port``, which keeps listening on ``[::]``.

.. toctree::
    :hidden:
    :maxdepth: 1

    Services <services>
    Settings <settings>
    Internals </reference/apps/harp_apps.dashboard>


Loading
:::::::

The dashboard application is loaded by default. You can :code:`--disable` it if you want.

.. code-block:: shell

    $ harp-proxy server ... --disable dashboard

.. todo::

    Implement CLI to load or not load an application.


Configuration
:::::::::::::

.. note::

    The dashboard is enabled by default and configured with reasonable defaults.

Main
----

Main settings for the dashboard.

.. literalinclude:: ./examples/main.yml
    :language: yaml

Internal implementation: :class:`DashboardSettings <harp_apps.dashboard.settings.DashboardSettings>`

Authentication
--------------

**The dashboard requires a sign-in, and there is no way to turn it off.** People sign in with a username and a password
at ``/signin``; with no account yet, the setup link HARP logs at start creates the first administrator. Accounts,
roles, sessions and the setup link are the business of the :doc:`auth application </apps/auth/index>`. Every route of
the dashboard port is behind a session, ``/metrics`` included; only the sign-in and setup pages, and the requests they
make, are reachable without one.

Configuring users in ``dashboard.auth`` is **deprecated**: they sign in with HTTP Basic, their passwords stay verified
from the configuration, and they are imported once as ``admin`` accounts.

.. literalinclude:: ./examples/auth.yml
    :language: yaml


.. literalinclude:: ./examples/auth.basic.yml
    :language: yaml

Internal implementation: :class:`BasicAuthSettings <harp_apps.dashboard.settings.auth.BasicAuthSettings>`

.. include:: ./_howto_auth_hash.rst

Each user is an account of the auth application, which gives it a role (``viewer``, ``editor`` or ``admin``) that
decides the pages and actions it may use. Users declared here are ``admin``.

A browser fetching a page without a session is sent to ``/signin``, except when ``dashboard.auth`` is configured, where
the Basic prompt is kept. The dashboard's own requests (``/api``) get a ``401`` without ``WWW-Authenticate``, so that a
session that ended never makes the browser ask for a Basic password.

.. note::

    ``dashboard.auth.type: none``, which served the dashboard to anyone, was removed: it is refused at start.


Metrics port
------------

``dashboard.metrics_port`` opens a second port serving only ``/metrics``, **unauthenticated by design**, so Prometheus
can scrape it without credentials. Any other path there answers 404. Keep it on a private network. See
:doc:`/operate/prometheus`.


Security headers
----------------

Every dashboard response carries ``X-Content-Type-Options: nosniff`` and ``X-Frame-Options: DENY`` and ``Referrer-Policy: same-origin``; the built
dashboard also sends a ``Content-Security-Policy`` that allows only its own scripts, styles and API, and forbids
framing (``frame-ancestors 'none'``). The dashboard cannot be embedded in another page.

Requests that change state (``PUT``, ``POST``, ``DELETE``) are refused unless they are ``application/json`` and come
from the dashboard itself: a cross-site ``Origin`` or ``Sec-Fetch-Site`` is answered ``403``, a missing JSON content
type ``415``. Scripts calling these routes must send ``Content-Type: application/json``.

Captured message bodies (``/api/blobs/{id}``) are served with ``Content-Disposition: attachment`` and
``Content-Security-Policy: sandbox; default-src 'none'``: opening one in a browser downloads it, and it never runs as
a page of the dashboard.


Dev Server
----------

Explicit configurations for the dashboard's micro frontend dev server, served by vitejs.

.. literalinclude:: ./examples/devserver.yml
    :language: yaml

.. admonition:: Internal

    You most likely don't need to configure the dev server unless you're working on harp's internals.

Enable/disable
--------------

To disable the dashboard globally, do not load the ``dashboard`` application.

.. code-block:: shell

    $ harp-proxy server ... --disable dashboard

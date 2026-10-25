HARP, the HTTP API Runtime Proxy
================================

HARP is an open-source proxy that sits between your application and the HTTP APIs it calls. It adds caching, a circuit
breaker, a rules engine and a searchable record of the traffic, without changes to your code other than the base URL.
It runs in your infrastructure, next to your application.

.. image:: https://img.shields.io/pypi/v/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: PyPI

.. image:: https://github.com/msqd/harp/actions/workflows/cicd.yml/badge.svg
    :target: https://github.com/msqd/harp/actions/workflows/cicd.yml
    :alt: CI/CD Pipeline Status

.. image:: https://readthedocs.org/projects/harp-proxy/badge/?version=stable
    :target: https://docs.harp-project.net/en/stable/
    :alt: Documentation

.. image:: https://img.shields.io/pypi/pyversions/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: Versions

----

**Community**: |badge_list| |badge_discord| |badge_contributors|

.. |badge_list| image:: https://img.shields.io/badge/Subscribe_to_release_announcements-085E9F?logo=maildotru
    :target: https://lists.harp-project.net/subscription/form
    :alt: Subscribe to release announcements

.. |badge_discord| image:: https://img.shields.io/badge/Join_our_discord_server-ffffff?logo=discord
    :target: https://discord.gg/uZeqBadpZQ
    :alt: Join our discord server

.. |badge_contributors| image:: https://img.shields.io/badge/contributors-8-orange
    :target: https://github.com/msqd/harp/graphs/contributors
    :alt: All Contributors

What it is, and what it is not
::::::::::::::::::::::::::::::

HARP is a proxy for outgoing HTTP calls, written in Python, with one local port per remote API. You point your
application at HARP instead of at the remote API, and HARP forwards the request. Along the way it can answer from its cache, stop sending traffic to a
failing server, apply your own rules, and record the exchange so you can look at it in a dashboard.

.. figure:: https://github.com/msqd/harp/raw/main/docs/images/diagrams/how-it-works-overview.svg
    :alt: Your applications call HARP, which calls the external APIs

HARP is released as ``0.x`` and is used by its authors in development and in production. Some features are less
polished than others and some APIs may still change between minor versions: the rules engine, for one, is documented as
a preview (see its `application page <https://docs.harp-project.net/en/stable/apps/rules/>`_). The `upgrade guide
<https://docs.harp-project.net/en/stable/operate/upgrading.html>`_ covers moving to 0.12 and the changes that came with
it.

Limits to know before relying on it:

* **Recording is best-effort.** Under load HARP sheds message detail first, then whole transactions, instead of slowing
  your traffic down (one known exception: a stalled database shared with the HTTP cache, `#1352
  <https://github.com/msqd/harp/issues/1352>`_). Treat the transaction record as an operational view, not as a complete
  account. A recorded response body is cut at 1 MiB (``proxy.max_recorded_body_size``). The `storage documentation
  <https://docs.harp-project.net/en/stable/apps/storage/>`_ gives the measured capacity and the memory it needs.
* **Streaming is not supported.** Server-sent events and long-polling do not work through HARP, and request bodies are
  read in full before they go upstream. See the `proxy application
  <https://docs.harp-project.net/en/stable/apps/proxy/>`_.
* **PostgreSQL is the production database.** Install it with the ``harp-proxy[postgresql]`` extra. The default SQLite
  storage lives in memory and is for development. MySQL and MariaDB are deprecated. See the `storage application
  <https://docs.harp-project.net/en/stable/apps/storage/>`_.

What you get
::::::::::::

* `Caching <https://docs.harp-project.net/en/stable/features/caching.html>`_ that follows HTTP caching headers (RFC 9111).
* A `circuit breaker <https://docs.harp-project.net/en/stable/features/circuit-breaker.html>`_ with pools of remote URLs
  and health probes.
* A `rules engine <https://docs.harp-project.net/en/stable/apps/rules/>`_ (preview) to change requests and
  responses with small Python scripts.
* An `audit log <https://docs.harp-project.net/en/stable/features/auditlog.html>`_ of the transactions, shown in a
  `dashboard <https://docs.harp-project.net/en/stable/apps/dashboard/>`_ protected by a login.
* `Prometheus metrics <https://docs.harp-project.net/en/stable/operate/prometheus.html>`_ on the dashboard port, behind
  its login (or on an optional, unauthenticated ``dashboard.metrics_port``).

.. figure:: https://github.com/msqd/harp/raw/main/docs/user/images/transactions.png
    :alt: The transactions list of the HARP dashboard

Try it
::::::

You need `uv <https://docs.astral.sh/uv/getting-started/installation/>`_, which also fetches the Python 3.13 that HARP
requires. Start a proxy to `httpbin.org <http://httpbin.org>`_ on port 4000, with the dashboard on port 4080:

.. code-block:: bash

    uvx -p 3.13 harp-proxy server --endpoint httpbin=4000:http://httpbin.org

The dashboard asks for a login. HARP prints a generated password for the ``admin`` user in its output, on a line
containing ``Dashboard login``. It changes at every start. To set your own users or to turn the login off, see the
`dashboard application <https://docs.harp-project.net/en/stable/apps/dashboard/>`_ (``dashboard.auth``, or
``--set dashboard.auth.type=none``, which leaves the dashboard open to anyone who can reach its port). Scrapers and
scripts calling port 4080 must send credentials, or use ``dashboard.metrics_port`` for Prometheus.

In another terminal, send a few requests through the proxy:

.. code-block:: bash

    curl "http://localhost:4000/get"
    curl -X POST "http://localhost:4000/post"

Then open http://localhost:4080 and go to the *Transactions* tab.

With Docker, the same thing is:

.. code-block:: bash

    docker run --init -it --rm -p 4000-4100:4000-4100 makersquad/harp-proxy server --endpoint httpbin=4000:http://httpbin.org

The proxy and the dashboard use the same ports, and the generated password is printed in the container output.

Where to go next
::::::::::::::::

The documentation is at https://docs.harp-project.net/en/stable/.

* `Quick start <https://docs.harp-project.net/en/stable/start/quick.html>`_: the first run, explained. The `user guide
  <https://docs.harp-project.net/en/stable/user/>`_ shows how to read the dashboard.
* `Run it in Docker <https://docs.harp-project.net/en/stable/start/docker.html>`_: image tags, a configuration file and
  Docker Compose.
* `Operate it in production <https://docs.harp-project.net/en/stable/operate/>`_: configuration, migrations, logging,
  metrics, upgrades.
* `Explore the features <https://docs.harp-project.net/en/stable/features/>`_: caching, circuit breaker, rules, audit
  log, one page each.
* `Extend it <https://docs.harp-project.net/en/stable/develop/>`_: write your own applications and customize the proxy.
* `Contribute <https://docs.harp-project.net/en/stable/contribute/>`_: set up the sources, the architecture and how to
  send a change.

HARP Community Edition is licensed under the LGPL 3.0 or later, see `LICENSE.rst
<https://github.com/msqd/harp/blob/main/LICENSE.rst>`_. To report a vulnerability, see `SECURITY.md
<https://github.com/msqd/harp/blob/main/SECURITY.md>`_.


People & Credits
::::::::::::::::

.. raw:: html

    <table>
      <tbody>
        <tr>
          <td align="center" valign="top" width="14.28%"><a href="https://www.makersquad.fr/"><img src="https://avatars.githubusercontent.com/u/30586?v=4?s=100" width="100px;" alt="Romain Dorgueil"/><br /><sub><b>Romain Dorgueil</b></sub></a><br /><a href="#business-hartym" title="Business development">💼</a> <a href="#ideas-hartym" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Documentation">📖</a> <a href="#example-hartym" title="Examples">💡</a> <a href="#financial-hartym" title="Financial">💵</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Tests">⚠️</a> <a href="https://github.com/msqd/harp/issues?q=author%3Ahartym" title="Bug reports">🐛</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/ArthurD1"><img src="https://avatars.githubusercontent.com/u/44548105?v=4?s=100" width="100px;" alt="Arthur Degonde"/><br /><sub><b>Arthur Degonde</b></sub></a><br /><a href="#ideas-ArthurD1" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Documentation">📖</a> <a href="#example-ArthurD1" title="Examples">💡</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Tests">⚠️</a> <a href="https://github.com/msqd/harp/issues?q=author%3AArthurD1" title="Bug reports">🐛</a></td>
          <td align="center" valign="top" width="14.28%"><a href="http://lenormand-julien.fr/"><img src="https://avatars.githubusercontent.com/u/13200639?v=4?s=100" width="100px;" alt="Lenormand Julien"/><br /><sub><b>Lenormand Julien</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=Lenormju" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=Lenormju" title="Documentation">📖</a> <a href="#ideas-Lenormju" title="Ideas, Planning, & Feedback">🤔</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/Synss"><img src="https://avatars.githubusercontent.com/u/540976?v=4?s=100" width="100px;" alt="Mathias Laurin"/><br /><sub><b>Mathias Laurin</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=Synss" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=Synss" title="Tests">⚠️</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/masterivanic"><img src="https://avatars.githubusercontent.com/u/62161915?v=4?s=100" width="100px;" alt="Ivanic"/><br /><sub><b>Ivanic</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=masterivanic" title="Code">💻</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/manu-paylead"><img src="https://avatars.githubusercontent.com/u/106162036?v=4?s=100" width="100px;" alt="Manu"/><br /><sub><b>Manu</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=manu-paylead" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=manu-paylead" title="Documentation">📖</a> <a href="#ideas-manu-paylead" title="Ideas, Planning, & Feedback">🤔</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/kocaemre"><img src="https://avatars.githubusercontent.com/u/110906681?v=4?s=100" width="100px;" alt="Emre K."/><br /><sub><b>Emre K.</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=kocaemre" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=kocaemre" title="Tests">⚠️</a></td>
        </tr>
        <tr>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/kta1kri"><img src="https://avatars.githubusercontent.com/u/77656895?v=4?s=100" width="100px;" alt="kta1kri"/><br /><sub><b>kta1kri</b></sub></a><br /><a href="#security-kta1kri" title="Security">🛡️</a></td>
        </tr>
      </tbody>
    </table>

* Sponsored by `Makersquad <https://www.makersquad.fr/>`_

`There are many ways you can contribute to HARP! <https://docs.harp-project.net/en/stable/contribute/index.html>`_

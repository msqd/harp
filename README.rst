HARP, an API Runtime Proxy
==========================

HARP is an open-source API Proxy toolkit designed to improve the reliability, performance, security, and observability
of the APIs you use. It runs in your infrastructure, close to your applications.

.. image:: https://img.shields.io/pypi/v/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: PyPI

.. image:: https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/harp
    :target: https://artifacthub.io/packages/helm/harp/harp-proxy
    :alt: Artifact Hub

.. image:: https://www.gitlab.com/makersquad/oss/harp/badges/0.8/pipeline.svg
    :target: https://www.gitlab.com/makersquad/oss/harp/pipelines
    :alt: GitLab CI/CD Pipeline Status

.. image:: https://readthedocs.org/projects/harp-proxy/badge/?version=0.8
    :target: https://docs.harp-proxy.net/en/0.8/
    :alt: Documentation

.. image:: https://img.shields.io/pypi/pyversions/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: Versions

----

**Quick links:** `Documentation <https://docs.harp-proxy.net/en/latest/>`_
| `Getting Started <https://docs.harp-proxy.net/en/latest/start/index.html>`_
| `Install (Docker) <https://docs.harp-proxy.net/en/latest/start/docker.html>`_
| `Install (PIP) <https://docs.harp-proxy.net/en/latest/start/python.html>`_
| `Repository (Git) <https://github.com/msqd/harp>`_
| `CI/CD <https://gitlab.com/makersquad/oss/harp/-/pipelines>`_

**Editions:** `HARP Community <https://harp-proxy.net/>`_ | `HARP Pro <https://www.getharp.eu/>`_ | `HARP Enterprise <https://www.getharp.eu/>`_

**Community**: |badge_list| |badge_discord| |badge_contributors|

.. |badge_list| image:: https://img.shields.io/badge/Subscribe_to_release_announcements-085E9F?logo=maildotru
    :target: https://lists.harp-proxy.net/subscription/form
    :alt: Subscribe to release announcements

.. |badge_discord| image:: https://img.shields.io/badge/Join_our_discord_server-ffffff?logo=discord
    :target: https://discord.gg/uZeqBadpZQ
    :alt: Join our discord server

.. |badge_contributors| image:: https://img.shields.io/badge/contributors-5-orange
    :target: https://github.com/msqd/harp/graphs/contributors
    :alt: All Contributors


*HARP is used both in development and production, and it works well for us. However, it is still under heavy active
development and some features may not be as polished as you expect, and some APIs may change.*

*We are actively looking for feedback, please reach out with your thoughts, ideas, rants or issues. We can help.*


What is HARP?
:::::::::::::

HARP is a python-based framework to build API proxies. From no-configuration 1 minute start to try it locally with an in
memory database to a full production ready proxy with multiple storage backends and custom filtering, it got you
covered.

The main goal is to improve the performance, reliability, security, and observability of the APIs you already use,
without changing anything except the base URL of your API calls. Ultimately, you can use HARP to "fix the Internet," or
at least the subset your application depends on.

Out of the box, you'll get standard-compliant caching (based on `hishel <https://hishel.com/>`_), a world class http
client (based on `httpx <https://www.python-httpx.org/>`_), a `circuit breaker
<https://docs.harp-proxy.net/en/latest/features/circuit-breaker.html>`_, a `python-based rules engine
<https://docs.harp-proxy.net/en/latest/features/rules.html>`_, an audit log and an `observation dashboard
<https://docs.harp-proxy.net/en/latest/features/dashboard.html>`_. The `features guide
<https://docs.harp-proxy.net/en/latest/features/index.html>`_ will tell you more.

.. figure:: https://docs.harp-proxy.net/en/latest/_images/overview.png
    :alt: HARP Proxy Overview
    :align: center

To instantly get insights on how your application is interacting with external services, you get a full searchable
transactions audit trail, with detailed information on each request and response.

.. figure:: https://docs.harp-proxy.net/en/latest/_images/transactions.png
    :alt: HARP Proxy Transactions
    :align: center

No more doubts about what happened. Now, you ***know***.

`Discover all HARP Proxy features <https://docs.harp-proxy.net/en/latest/features/index.html>`_


Getting Started
:::::::::::::::

Refer to the `Getting Started Guide <https://docs.harp-proxy.net/en/latest/start/index.html>`_ to learn how to install
and run your first proxy (it's easy, we promise).

You can install and run HARP Proxy `using Docker <https://docs.harp-proxy.net/en/latest/start/docker.html>`_ (easier and
more language-agnostic) or `using a Python package <https://docs.harp-proxy.net/en/latest/start/python.html>`_ (for more
control and customization).


How it works?
:::::::::::::

Overview
--------

.. figure:: https://github.com/msqd/harp/raw/0.8/docs/images/HowItWorks-Overview.png
    :alt: An overview of how HARP works in your system
    :align: center

* **Easy Integration:** Integrating with your application is a breeze, because it speaks the same language you already
  use: HTTP. Simply run the proxy, update your API endpoints, and you're ready to go. No complex setup or extensive
  configuration required. Of course, everything is modular and configurable, so you'll be able to fine-tune for your
  taste later.
* **Reduced Network Distance:** As a *nearline* proxy, HARP minimizes the network distance between your application
  and external services, when possible, using standard techniques like caching or prefetching. This leads to faster
  response times and improved overall performance of your application, even before any configuration is done.
* **Simplified Development:** HARP eliminates the need for writing extensive code for functionalities such as caching,
  monitoring, alerting, rate limiting, circuit breaking, retries, tracing, logging, and more. These features can be
  easily delegated to the proxy, reducing the amount of code you need to write and maintain.
* **Seamless HTTP Integration:** HARP seamlessly integrates with your application using the HTTP protocol. This means
  that the integration or removal cost is virtually zero, or even negative when considering the reduction in code you
  won't need to write.

`Read the full documentation <https://docs.harp-proxy.net/en/latest/>`_


Hub to external services
------------------------

.. figure:: https://github.com/msqd/harp/raw/0.6/docs/images/HowItWorks-OverviewMultipleApps.png
    :alt: An overview of how HARP works in your system when you have multiple consumers
    :align: center

* **Mutualize Client Logic**: Having n API consumers does not mean you have to implement n times each client-side
  feature. Use HARP as a hub and greatly reduce the amount of client code you need to write and maintain.
* **Observes and Controls**: You get a central place to observe and control all your API interactions.
* **Grow and Scale**: As your company grows and develop new applications, you can leverage the work done on existing
  external services without having to write a single new line of code.


Service
-------

Within the service, harp runs one or more proxies, each one listening to one port to instrument your external API calls
with the features you need (auditing, caching, alerting, circuit breaker switch, health checks, etc.).

Each proxy is configured to intercept and forward requests to a specific external API, with independent configuration.

An additional (optional) port serves a dashboard to observe your proxies in real-time.

.. figure:: https://github.com/msqd/harp/raw/0.8/docs/images/HowItWorks-Service.png
    :alt: What happens within the harp service
    :align: center

* **Features**: Harp comes builtin with a set of industry-standard client side features that you can leverage with a few
  lines of configuration.
* **Flexibility**: Each feature is optional, and it's up to you to chose the setup that fits your needs.
* **Customizable**: You can write code to extend the proxy features, using the same interface as all the builtin
  features. It guarantees that you can basically implement pretty much anything that make sense inbetween your
  applications and the external services.


Proxy
-----

As an HTTP Proxy, HARP does not change anything to the way you communicate with the external services. You were speaking
HTTP before, you will still speak HTTP. The only change needed in your applications configuration to plug or unplug HARP
is the base endpoint of the external services. In a modern 12factor-like application, it usually only means changing an
environment variable.

.. figure:: https://github.com/msqd/harp/raw/0.8/docs/images/HowItWorks-Proxy.png
    :alt: What happens within one harp proxy
    :align: center

* **Reversibility**: By requiring 0 code change on your application side (except endpoint url configuration, that
  should be outside the code if you follow the 12factor principles), HARP can be plugged and unplugged at a very low
  cost. You have absolutely no vendor lock-in.
* **Sidecar**: Harp runs in your infrastructure, implementing the client side features right next to your application.
  The service is fast, and the minimum network distance between your application and the proxy makes it even faster.
* **Open Core**: Harp is an open software. The core and reference implementation of the proxy is open source, and you
  can extend it to fit your needs.

Proxy features
--------------

Here is a non-exhaustive list of HARP Proxy's main features:

* `Configuration <https://docs.harp-proxy.net/en/latest/features/configuration.html>`_
* `Dashboard <https://docs.harp-proxy.net/en/latest/features/dashboard.html>`_
* `Proxy <https://docs.harp-proxy.net/en/latest/features/proxy.html>`_
* `Audit Log <https://docs.harp-proxy.net/en/latest/features/auditlog.html>`_
* `Caching <https://docs.harp-proxy.net/en/latest/features/caching.html>`_
* `Circuit Breaker <https://docs.harp-proxy.net/en/latest/features/circuit-breaker.html>`_
* `Rules Engine <https://docs.harp-proxy.net/en/latest/features/rules.html>`_

You can `read more about all HARP Proxy features <https://docs.harp-proxy.net/en/latest/features/index.html>`_ in the
`Features Guide <https://docs.harp-proxy.net/en/latest/features/index.html>`_.


People & Credits
::::::::::::::::

.. raw:: html

    <table>
      <tbody>
        <tr>
          <td align="center" valign="top" width="14.28%"><a href="https://www.makersquad.fr/"><img src="https://avatars.githubusercontent.com/u/30586?v=4?s=100" width="100px;" alt="Romain Dorgueil"/><br /><sub><b>Romain Dorgueil</b></sub></a><br /><a href="#business-hartym" title="Business development">💼</a> <a href="#ideas-hartym" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Documentation">📖</a> <a href="#example-hartym" title="Examples">💡</a> <a href="#financial-hartym" title="Financial">💵</a> <a href="https://github.com/msqd/harp/commits?author=hartym" title="Tests">⚠️</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/ArthurD1"><img src="https://avatars.githubusercontent.com/u/44548105?v=4?s=100" width="100px;" alt="Arthur Degonde"/><br /><sub><b>Arthur Degonde</b></sub></a><br /><a href="#ideas-ArthurD1" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Documentation">📖</a> <a href="#example-ArthurD1" title="Examples">💡</a> <a href="https://github.com/msqd/harp/commits?author=ArthurD1" title="Tests">⚠️</a></td>
          <td align="center" valign="top" width="14.28%"><a href="http://lenormand-julien.fr/"><img src="https://avatars.githubusercontent.com/u/13200639?v=4?s=100" width="100px;" alt="Lenormand Julien"/><br /><sub><b>Lenormand Julien</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=Lenormju" title="Code">💻</a> <a href="https://github.com/msqd/harp/commits?author=Lenormju" title="Documentation">📖</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/Synss"><img src="https://avatars.githubusercontent.com/u/540976?v=4?s=100" width="100px;" alt="Mathias Laurin"/><br /><sub><b>Mathias Laurin</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=Synss" title="Code">💻</a></td>
          <td align="center" valign="top" width="14.28%"><a href="https://github.com/masterivanic"><img src="https://avatars.githubusercontent.com/u/62161915?v=4?s=100" width="100px;" alt="Ivanic"/><br /><sub><b>Ivanic</b></sub></a><br /><a href="https://github.com/msqd/harp/commits?author=masterivanic" title="Code">💻</a></td>
        </tr>
      </tbody>
    </table>

* Sponsored by `Makersquad <https://www.makersquad.fr/>`_

`There are many ways you can contribute to HARP! <https://docs.harp-proxy.net/en/latest/contribute/index.html>`_

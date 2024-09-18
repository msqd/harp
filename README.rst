HARP – Harp, an API Runtime Proxy
=================================

HARP is a powerful sidecar proxy service designed to elevate the reliability, performance, security, and observability
of your application's external API interactions. Think of it as a reverse API gateway or a nearline service mesh for
external APIs.

To be notified when we release new features, you can `subscribe to the release announcements <https://lists.harp-proxy.net/subscription/form>`_.
We do not send anything unrelated to the lists you subscribed to, and we do not communicate your personnal informations with anyone. And
of course, you can unsubscribe anytime using the unsubscribe link sent with all mails.

**HARP is released as an Early Access Preview.**

.. image:: https://img.shields.io/pypi/v/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: PyPI

.. image:: https://www.gitlab.com/makersquad/oss/harp/badges/0.6/pipeline.svg
    :target: https://www.gitlab.com/makersquad/oss/harp/pipelines
    :alt: GitLab CI/CD Pipeline Status

.. image:: https://readthedocs.org/projects/harp-proxy/badge/?version=0.6
    :target: https://docs.harp-proxy.net/en/0.6/
    :alt: Documentation

.. image:: https://img.shields.io/pypi/pyversions/harp-proxy.svg
    :target: https://pypi.python.org/pypi/harp-proxy
    :alt: Versions

*Although we use HARP for production workloads, it is still under heavy active development and some features
may not be available, or it may not be suitable for your applications. We are actively looking for feedback, please
reach out with your thoughts, ideas, rants or issues. We can help.*

**Quick links:** `Documentation <https://docs.harp-proxy.net/en/latest/>`_
| `Getting Started <https://docs.harp-proxy.net/en/latest/start/index.html>`_
| `Install (Docker) <https://docs.harp-proxy.net/en/latest/start/docker.html>`_
| `Install (PIP) <https://docs.harp-proxy.net/en/latest/start/python.html>`_
| `Repository (Git) <https://github.com/msqd/harp>`_
| `Issues <https://github.com/msqd/harp/issues>`_
| `CI/CD <https://gitlab.com/makersquad/oss/harp/-/pipelines>`_


What is HARP Proxy?
:::::::::::::::::::

HARP Proxy is a fast open-source API proxy that you can use in development or production to improve the reliability,
performance, security, and observability of your application's external API interactions.

You list your external API endpoints in the configuration, update your consumer's base endpoints to hit the proxy and
HARP will intercept and forward requests to these, with additional instrumentation.

Out of the box, you'll get standard-compliant caching, a world class http client (with retries, timeouts, etc.), and
a vizualization dashboard to observe everything.

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

.. figure:: https://github.com/msqd/harp/raw/0.6/docs/images/HowItWorks-Overview.png
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

.. figure:: https://github.com/msqd/harp/raw/0.6/docs/images/HowItWorks-Service.png
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

.. figure:: https://github.com/msqd/harp/raw/0.6/docs/images/HowItWorks-Proxy.png
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

* Core contributors:

  - `Arthur Degonde <https://github.com/ArthurD1>`_
  - `Romain Dorgueil <https://github.com/hartym>`_

* Original idea, design, and development:

  - `Romain Dorgueil <https://github.com/hartym>`_

* Sponsored by `Makersquad <https://www.makersquad.fr/>`_

`There are many ways you can contribute to HARP! <https://docs.harp-proxy.net/en/latest/contribute/index.html>`_

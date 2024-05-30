HARP – Harp, an API Runtime Proxy
=================================

HARP is a powerful sidecar proxy service designed to elevate the reliability, performance, security, and observability
of your application's external API interactions. Think of it as a reverse API gateway or a nearline service mesh for
external APIs.


.. important::

    HARP is released as an Early Access Preview.

    Although we already use it for production workloads, it is still under heavy active development and some features
    may not be available, or it may not be suitable for your applications.

    We are actively looking for feedback, so please don't hesitate to reach out to us with your thoughts, ideas, or
    issues. We are here to help you and make HARP better for everyone.


**Quick links:** `Documentation <https://harp-proxy.readthedocs.io/en/latest/>`_ | `Repository <https://github.com/msqd/harp>`_ | `Issues <https://github.com/msqd/harp/issues>`_ | `CI/CD <https://gitlab.com/makersquad/oss/harp/-/pipelines>`_


How it works?
:::::::::::::

Overview
--------

.. image:: docs/images/HowItWorks-Overview.png
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

`Read the full documentation <https://harp-proxy.readthedocs.io/en/latest/>`_


Service
-------

.. image:: docs/images/HowItWorks-Service.png
    :alt: What happens within the harp service
    :align: center

Within the service, harp runs one or more proxies, each one listening to one port to instrument your external API calls
with the features you need (auditing, caching, alerting, circuit breaker switch, health checks, etc.).

An additional (optional) port serves a dashboard to observe your proxies in real-time.


Proxy
-----

.. image:: docs/images/HowItWorks-Proxy.png
    :alt: What happens within one harp proxy
    :align: center

Each proxy is configured to intercept and forward requests to a specific external API, with independent configuration.

The instance's storage is used by each proxy to store whatever it needs, depending on the activated features.

Proxy features
--------------


Quick start
:::::::::::

Install

TODO: fix once released

Run

TODO: fix once released

Read the docs

TODO: fix once released

Tell us what you think

TODO: fix once released


Credits
:::::::

* Core contributors:

  - `Arthur Degonde <https://github.com/ArthurD1>`_
  - `Romain Dorgueil <https://github.com/hartym>`_

* Original idea, design, and development:

  - `Romain Dorgueil <https://github.com/hartym>`_

* Sponsored by `Makersquad <https://www.makersquad.fr/>`_

`There are many ways you can contribute to HARP! <https://harp-proxy.readthedocs.io/en/latest/contribute/>`_

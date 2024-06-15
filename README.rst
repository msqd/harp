HARP – Harp, an API Runtime Proxy
=================================

HARP is a powerful sidecar proxy service designed to elevate the reliability, performance, security, and observability
of your application's external API interactions. Think of it as a reverse API gateway or a nearline service mesh for
external APIs.

**HARP is released as an Early Access Preview.**

*Although we already use it for production workloads, it is still under heavy active development and some features
may not be available, or it may not be suitable for your applications. We are actively looking for feedback, please
reach out with your thoughts, ideas, rants or issues. We can help.*


**Quick links:** `Documentation <https://harp-proxy.readthedocs.io/en/latest/>`_
| `Getting Started <https://harp-proxy.readthedocs.io/en/latest/start/index.html>`_
| `Install (Docker) <https://harp-proxy.readthedocs.io/en/latest/start/docker.html>`_
| `Install (PIP) <https://harp-proxy.readthedocs.io/en/latest/start/python.html>`_
| `Repository (Git) <https://github.com/msqd/harp>`_
| `Issues <https://github.com/msqd/harp/issues>`_
| `CI/CD <https://gitlab.com/makersquad/oss/harp/-/pipelines>`_


How it works?
:::::::::::::

Overview
--------

.. figure:: https://github.com/msqd/harp/raw/dev/docs/images/HowItWorks-Overview.png
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


Hub to external services
------------------------

.. figure:: https://github.com/msqd/harp/raw/dev/docs/images/HowItWorks-OverviewMultipleApps.png
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

.. figure:: https://github.com/msqd/harp/raw/dev/docs/images/HowItWorks-Service.png
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

.. figure:: https://github.com/msqd/harp/raw/dev/docs/images/HowItWorks-Proxy.png
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

.. note:: (TODO) Add a list of features with links to the documentation.


Credits
:::::::

* Core contributors:

  - `Arthur Degonde <https://github.com/ArthurD1>`_
  - `Romain Dorgueil <https://github.com/hartym>`_

* Original idea, design, and development:

  - `Romain Dorgueil <https://github.com/hartym>`_

* Sponsored by `Makersquad <https://www.makersquad.fr/>`_

`There are many ways you can contribute to HARP! <https://harp-proxy.readthedocs.io/en/latest/contribute/>`_

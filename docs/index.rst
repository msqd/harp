Harp — HTTP API Runtime Proxy
=============================

.. image:: images/logo.png
   :alt: HARP logo
   :align: center

HARP operates as a sidecar proxy that sits between your application and remote APIs, elevating their reliability,
performance, and security. By doing so, it also provides observability and reduces the amount of userland code required
for common non-business functionalities.

Whether you are in the development phase or ready for production, HARP serves as a versatile tool that caters to
different purposes.

.. figure:: images/HowItWorks-Proxy.png
   :alt: Basic proxy setup from the quickstart tl;dr

The core runtime of HARP primarily consists of two components: a proxy (or a set of proxies) and a dashboard. Each proxy
is responsible for forwarding requests to its endpoint, while the dashboard allows you to observe the requests passing
through the proxies.

HARP adopts a modular approach, where all features are implemented as independent and composable modules known as
"applications." These applications can be enabled, disabled, extended, or arranged in different configurations to suit
your specific requirements. While HARP provides sensible defaults to get you up and running quickly, it also offers
limitless flexibility, allowing you to customize the proxy according to your unique needs.


.. table::
    :class: jumbo-toc
    :widths: 50 50

    +--------------------------------------------------------+--------------------------------------------------------+
    | :doc:`Start Guide </start/index>`                                                                               |
    |                                                                                                                 |
    | Install and run your first proxy.                                                                               |
    |                                                                                                                 |
    | - :doc:`/start/quick`                                                                                           |
    | - :doc:`Using Docker </start/docker>`                                                                           |
    | - :doc:`Using Python </start/python>`                                                                           |
    | - :doc:`From Sources </start/sources>`                                                                          |
    +--------------------------------------------------------+--------------------------------------------------------+
    | :doc:`User's Guide </user/index>`                      | :doc:`Operator's Guide </operate/index>`               |
    |                                                        |                                                        |
    | Explore the user interface.                            | Configure and watch.                                   |
    |                                                        |                                                        |
    | - :doc:`/user/overview`                                | - :doc:`/operate/configure/index`                      |
    | - :doc:`/user/transactions`                            | - :doc:`/operate/runtime`                              |
    | - :doc:`/user/system`                                  |                                                        |
    | - :doc:`/user/performances`                            |                                                        |
    +--------------------------------------------------------+--------------------------------------------------------+
    | :doc:`Developer's Guide </develop/index>`              | :doc:`Contributor's Guide </contribute/index>`         |
    |                                                        |                                                        |
    | Enhance and extend.                                    | Dive in the internals.                                 |
    |                                                        |                                                        |
    | - :doc:`/develop/run`                                  | - :doc:`/contribute/introduction`                      |
    | - :doc:`/develop/customize`                            | - :doc:`/contribute/applications/index`                |
    | - :doc:`/develop/extend`                               | - :doc:`/contribute/roadmap`                           |
    +--------------------------------------------------------+--------------------------------------------------------+
    | :doc:`Reference <reference/index>`                                                                              |
    |                                                                                                                 |
    | Implementation details.                                                                                         |
    |                                                                                                                 |
    | - :doc:`Command Line Reference </reference/commandline/index>`                                                  |
    | - :doc:`Core API Reference </reference/core/harp>`                                                              |
    | - :doc:`Applications Reference </reference/apps/harp_apps>`                                                     |
    +--------------------------------------------------------+--------------------------------------------------------+


Table of Content
::::::::::::::::

.. toctree::
   :maxdepth: 2

   /start/index
   /user/index
   /operate/index
   /develop/index
   /contribute/index
   /apps/index
   /reference/index
   /faq


Indices and tables
::::::::::::::::::

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

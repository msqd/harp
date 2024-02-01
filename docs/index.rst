Harp — HTTP API Runtime Proxy
=============================

HARP operates as a sidecar proxy that sits between your application and remote APIs, elevating their reliability,
performance, and security. By doing so, it also provides observability and reduces the amount of userland code required
for common non-business functionalities.

Whether you are in the development phase or ready for production, HARP serves as a versatile tool that caters to
different purposes.

.. figure:: images/tldr.png
   :alt: Basic proxy setup from the quickstart tl;dr

The core runtime of HARP primarily consists of two components: a proxy and a dashboard. The proxy is responsible for
forwarding requests to various endpoints, while the dashboard allows you to observe the requests passing through the
proxy.

HARP adopts a modular approach, where all features are implemented as independent and composable modules known as
"applications." These applications can be enabled, disabled, extended, or arranged in different configurations to suit
your specific requirements. While HARP provides sensible defaults to get you up and running quickly, it also offers
limitless flexibility, allowing you to customize the proxy according to your unique needs.


Content
:::::::

.. toctree::
   :maxdepth: 2

   quickstart/index
   features/index
   installation/index
   commandline/index
   configuration/index
   reference/index
   development/index
   faq

Indices and tables
::::::::::::::::::

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

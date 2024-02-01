HARP – Harp, an API Runtime Proxy
=================================

HARP is a powerful sidecar proxy service designed to elevate the reliability, performance, security, and observability
of your application's external API interactions. Think of it as a reverse API gateway or a nearline service mesh for 
external APIs.

.. image:: docs/images/how-it-works.png

* Easy Integration: With HARP, integrating with your application is a breeze. Simply run the proxy, update your API
  endpoints, and you're ready to go. No complex setup or extensive configuration required.
* Reduced Network Distance: As a nearline proxy, HARP minimizes the network distance between your application and 
  external services. This optimization leads to faster response times and improved overall performance.
* Simplified Development: HARP eliminates the need for writing extensive code for functionalities such as caching,
  monitoring, alerting, rate limiting, circuit breaking, retries, tracing, logging, and more. These features can be
  easily delegated to the proxy, reducing the amount of code you need to write and maintain.
* Seamless HTTP Integration: HARP seamlessly integrates with your application using the HTTP protocol. This means
  that the integration or removal cost is virtually zero, or even negative when considering the reduction in code you
  won't need to write.


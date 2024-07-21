Lifecycle
=========

During the lifecycle of a transaction, 4 hooks are available:

.. raw:: html
    :file: sequence.svg

* :doc:`on_request <on_request>` will trigger on each request received by the proxy controller, allowing early filtering/tuning of a
  request.
* :doc:`on_remote_request <on_remote_request>` will trigger every time the proxy needs to actually send an http request
  to the remote endpoint. This won't happen for requests that HIT the cache, or that does not need remote access for
  whatever reason. It allows to filter the external http request just before it's sent out.
* :doc:`on_remote_response <on_remote_response>` will trigger every time the proxy receives a response from the remote
  endpoint. It allows to filter the response before it's processed by the proxy. For example, it's a good place to
  override the response cache-control headers to tune the cache behavior for some transactions.
* :doc:`on_response <on_response>` will trigger every time the proxy is about to send a response to the client.

You can also use the special ``*`` event pattern to match all events, but beware that the available locals are not
the same for all events.


.. toctree::
    :hidden:
    :maxdepth: 1

    on_request
    on_remote_request
    on_remote_response
    on_response

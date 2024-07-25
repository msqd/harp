``on_remote_request``
=====================

The ``on_remote_request`` lifecycle event is triggered when the proxy is about to send a request to the remote server.

Please note that unlike ``on_request``, this is not guaranteed to happen for every transaction. For example, if a
previous event forged a response, or if the request is served from the cache, this event will not be triggered.

This allows to write logic that is specific for outgoing requests.

.. tab-set-code::

    .. code:: toml

        [rules."*"."*"]
        on_remote_request = """
        print(f'Hello, {request}.')
        """

    .. code:: yaml

        rules:
          "*":
            "*":
              on_remote_request: |
                print(f'Hello, {request}.')

The event instance passed to :doc:`on_remote_request` lifecycle event scripts is a
:class:`HttpClientFilterEvent <harp_apps.http_client.events.HttpClientFilterEvent>`.

.. note::

    The ``request`` and ``response`` (if set) variables are instances of :class:`httpx.Request` and
    :class:`httpx.Response`.


Adding a header
:::::::::::::::

You can add a header to the outgoing request:

.. code-block:: toml

    [rules."*"."*"]
    on_remote_request = """
    request.headers['X-Hello'] = 'World'
    """


Forging a response
::::::::::::::::::

If a :class:`Response <httpx.Response>` is set in this event, the outgoing request will not be sent, and your response
will be used instead.

.. code-block:: toml

    [rules."*"."*"]
    on_remote_request = """
    from httpx import Response
    response = Response(200, content=b'Hello, World!')
    """

Context reference
:::::::::::::::::

The following variables are available in the context of the ``on_remote_request`` lifecycle event:

- ``logger``: the logger instance.
- ``event``: the :class:`HttpClientFilterEvent <harp_apps.http_client.events.HttpClientFilterEvent>` instance.
- ``endpoint``: the endpoint name for this transaction, as defined in your configuration.
- ``request``: the prepared :class:`httpx.Request` instance, ready to be sent.
- ``response``: an eventual :class:`httpx.Response` instance, but most probably None. Set this to a
  :class:`httpx.Response` to forge a response, bypassing the remote request.
- ``stop_propagation``: a function to stop the event propagation to the next event in the chain.

``on_request``
==============

The ``on_request`` lifecycle event happens on each request received by the proxy, before it even considers proxying
anything anywhere.


.. tab-set-code::

    .. code:: toml

        [rules."*"."*"]
        on_request = """
        print(f'Hello, {request}.')
        """

    .. code:: yaml

        rules:
          "*":
            "*":
              on_request: |
                print(f'Hello, {request}.')

The event instance passed to :doc:`on_request` lifecycle event scripts is a
:class:`ProxyFilterEvent <harp_apps.proxy.events.ProxyFilterEvent>` instance.

The same event instance will be passed to :doc:`on_response`, later in the lifecycle.


Patching the incoming request
:::::::::::::::::::::::::::::

You get a chance to modify the request before the proxy logic kicks in:

.. code-block:: toml

    [rules."*"."*"]
    on_request = """
    request.headers['X-Hello'] = 'World'
    """


Forging a response
::::::::::::::::::

If a :class:`Response <harp.http.HttpResponse>` is set in this event, the proxy will not be involved at all.

.. code-block:: toml

    [rules."*"."*"]
    on_request = """
    from harp.http import HttpResponse
    response = HttpResponse('Hello, World!')
    """

It's defined and dispatched by the ``proxy`` application, within the
:class:`HttpProxyController <harp_apps.proxy.controllers.HttpProxyController>` request handler.


Context reference
:::::::::::::::::

The following variables are available in the context of the ``on_request`` lifecycle event:

- ``logger``: the logger instance.
- ``event``: the :class:`ProxyFilterEvent <harp_apps.proxy.events.ProxyFilterEvent>` instance.
- ``endpoint``: the endpoint name for this transaction, as defined in your configuration.
- ``request``: the :class:`HttpRequest <harp.http.HttpRequest>` instance.
- ``response``: an eventual :class:`HttpResponse <harp.http.HttpResponse>` instance, but most probably None. Set this to
  a :class:`HttpResponse <harp.http.HttpResponse>` instance to short-circuit the proxying logic.
- ``stop_propagation``: a function to stop the event propagation to the next event in the chain.

.. warning::

    Don't use ``stop_propagation`` for now, as it will stop the whole lifecycle processing
    (`whistle#18 <https://github.com/python-whistle/whistle/issues/18>`_).

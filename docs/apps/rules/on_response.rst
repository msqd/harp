``on_response``
===============

The ``on_response`` lifecycle event is triggered before the response is sent back to the client, but after the proxy
logic has been executed, if relevant. This logic may have been bypassed by various mechanisms, such as a forged response
set by the ``on_request`` lifecycle event, or partially bypassed, for example if the proxy request did ``HIT`` the
cache.

.. tab-set-code::

    .. code:: toml

        [rules."*"."*"]
        on_response = """
        print(f'Goodbye, {response}.')
        """

    .. code:: yaml

        rules:
          "*":
            "*":
              on_response: |
                print(f'Goodbye, {response}.')


The event instance passed to :doc:`on_response` lifecycle event scripts is a
:class:`ProxyFilterEvent <harp_apps.proxy.events.ProxyFilterEvent>` instance.

The same event instance was passed to :doc:`on_request`, earlier in the lifecycle.

Patching the outgoing response
::::::::::::::::::::::::::::::

You can modify the response before it's sent back to the client:

.. code-block:: toml

    [rules."*"."*"]
    on_response = """
    response.headers['X-Goodbye'] = 'World'
    """


Switching the response
::::::::::::::::::::::

Although the reason may be debatable, if you need to, you can replace the response entirely:

.. code-block:: toml

    [rules."*"."*"]
    on_response = """
    from harp.http import HttpResponse
    response = HttpResponse('Goodbye, World!')
    """

The event instance passed to ``on_response`` lifecycle event scripts is a :class:`ProxyFilterEvent


Context reference
:::::::::::::::::

The following variables are available in the context of the ``on_response`` lifecycle event:

- ``logger``: the logger instance.
- ``event``: the :class:`ProxyFilterEvent <harp_apps.proxy.events.ProxyFilterEvent>` instance.
- ``endpoint``: the endpoint name for this transaction, as defined in your configuration.
- ``request``: the :class:`HttpRequest <harp.http.HttpRequest>` instance.
- ``response``: the :class:`HttpResponse <harp.http.HttpResponse>` instance. You can amend or replace it.
- ``stop_propagation``: a function to stop the event propagation to the next event in the chain.

.. warning::

    Don't use ``stop_propagation`` for now, as it will stop the whole lifecycle processing
    (`whistle#18 <https://github.com/python-whistle/whistle/issues/18>`_).

``on_remote_response``
======================

The ``on_remote_response`` lifecycle event is triggered after the response is received from the remote server.

Please note that unlike ``on_response``, this is not guaranteed to happen for every transaction (won't happen for cached
or bypassed requests).

This allows to write logic that is specific for remote responses.

.. tab-set-code::

    .. code:: toml

        [rules."*"."*"]
        on_remote_response = """
        print(f'Hello, {response}.')
        """

    .. code:: yaml

        rules:
          "*":
            "*":
              on_remote_response: |
                print(f'Hello, {response}.')

The event instance passed to :doc:`on_remote_response` lifecycle event scripts is a
:class:`HttpClientFilterEvent <harp_apps.http_client.events.HttpClientFilterEvent>`.

.. note::

    The ``request`` and ``response`` (if set) variables are instances of :class:`httpx.Request` and
    :class:`httpx.Response`.


Adding a response header
::::::::::::::::::::::::

You can add a header to the incoming response:

.. code-block:: toml

    [rules."*"."*"]
    on_remote_response = """
    response.headers['X-Goodbye'] = 'World'
    """


Overriding the Cache-Control
::::::::::::::::::::::::::::

You can override the Cache-Control header of the incoming response to override the default caching behavior.

This will disable caching (although you will prefer to set this on the request side):

.. code-block:: toml

    [rules."*"."*"]
    on_remote_response = """
    response.headers['Cache-Control'] = 'no-cache'
    """

Or if you want to cache everything for one hour:

.. code-block:: toml

    [rules."*"."*"]
    on_remote_response = """
    response.headers['Cache-Control'] = 'public, max-age=3600'
    """

Switching the response
::::::::::::::::::::::

Although the reason may be debatable, if you need to, you can replace the response entirely:

.. code-block:: toml

    [rules."*"."*"]
    on_remote_response = """
    from httpx import Response
    response = Response(200, content=b'Goodbye, World!')
    """

Context reference
:::::::::::::::::

The following variables are available in the context of the ``on_remote_response`` lifecycle event:

- ``logger``: the logger instance.
- ``event``: the :class:`HttpClientFilterEvent <harp_apps.http_client.events.HttpClientFilterEvent>` instance.
- ``request``: the :class:`httpx.Request` instance.
- ``response``: the :class:`httpx.Response` instance. You can amend or replace it.
- ``stop_propagation``: a function to stop the event propagation to the next lifecycle event.

.. warning::

    Don't use ``stop_propagation`` for now, as it will stop the whole lifecycle processing
    (`whistle#18 <https://github.com/python-whistle/whistle/issues/18>`_).

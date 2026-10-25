Events
======

.. tags:: applications

The ``harp_apps.events`` application writes the events that matter to operators without being control-plane actions
(a breaker opening on its own, a failed sign-in) to the logs. An event reaches the log only if the code that declares it
marked it ``loggable`` (see :ref:`events-loggable`): a configuration cannot add one, so per-request events such as
``proxy.transaction.started`` can never be logged this way.

Each event is one structured line on the ``harp.events`` logger, with ``kind: event``, the ``event_id``, the ``outcome``
and the ``details`` the event declares. Routing follows the logging configuration: ``LOGGING_FORMAT=json`` for JSON
lines, ``LOGGING_EVENT_LOG`` for the level of the logger (``info`` by default). Collect the lines with your own
collector, filtering on ``logger: harp.events`` or ``kind: event``.

Settings
::::::::

``muted``
    List of ``loggable`` event ids not to write. Default: none. Naming an event that is not ``loggable``, or unknown,
    stops HARP at startup with the list of the events you may name.

.. code-block:: yaml

    events:
      muted:
        - the.event.id

Loading
:::::::

The ``events`` application is loaded by default. Disabling it (``events.enabled: false``) silences all loggable events.

Notifications
=============

.. tags:: applications

.. versionadded:: 0.7

The ``notifications`` application is a simple way to send notifications to a webhook.
Currently the application supports sending notifications to Slack and Google Chat.
Notificaitons will be sent when an error occurs within a transaction.

The notification will include information about the error and the transaction that caused it.

.. note:: The notifications application is not loaded by default. You need to add it to your configuration file.

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.notifications>



Configuration
:::::::::::::

To configure the notifications application, you need to add the following settings to your configuration file.
The Notifications application can work with multiple services at the same time.

.. literalinclude:: ./examples/main.yml
    :language: yaml

If you want the notifications to include a link to your dashboard, you need to add the `public_url` settings to your dashboard configuration.

.. literalinclude:: ./examples/dashboard.yml
    :language: yaml


Delivery
::::::::

Notifications are queued and sent in the background: they never delay or change the response the client receives,
whatever the webhooks do.

``timeout``
    Seconds each sender has to deliver a notification (default ``5``). A sender that is too slow or that fails is
    logged at warning level, and the other senders are not affected.

``queue_size``
    Maximum number of notifications waiting to be sent (default ``100``). During a burst of errors, notifications
    beyond that limit are dropped and logged at warning level.

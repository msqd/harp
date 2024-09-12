Telemetry
=========

.. tags:: applications

.. versionadded:: 0.5

The ``harp_apps.telemetry`` application is responsible for sending anonymous usage statistics. This helps developers
understand how the application is being used and identify potential areas for improvement. The telemetry data includes
information about the platform, installed applications, and usage patterns.

.. toctree::
    :hidden:
    :maxdepth: 1

    Internals </reference/apps/harp_apps.telemetry>


Overview
--------

The Telemetry application collects and sends anonymous usage data to a remote server at regular intervals. This data
helps in analyzing the application’s usage patterns and improving its performance and features.

Features
--------

- **Anonymous Data Collection:** Ensures user privacy while collecting usage statistics.
- **Regular Reporting:** Sends data periodically to provide continuous insights.
- **Platform Detection:** Identifies the operating system and environment details.
- **Configuration Options:** Allows customization of telemetry settings and endpoints.

Loading
-------

The Telemetry application is loaded by default when using the harp start command.

Configuration
-------------
The Telemetry application can be disabled using the following command:

.. code-block:: bash

    harp start ... --disable telemetry


The internal implementation leverages the following class:

- :class:`TelemetryManager <harp_apps.telemetry.manager.TelemetryManager>`

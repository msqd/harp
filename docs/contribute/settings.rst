Settings and Configuration
==========================

A few tools are available for your applications to be configurable by the end-user.


Writing a Settings class
::::::::::::::::::::::::

Each configurable application should have a `settings.py` file that defines a `Settings` class. This is a convention
and is not enforced technically, but let's stick to the standard.

.. code-block:: python

    from harp.config import BaseSettings, settings_dataclass

    @settings_dataclass
    class AcmeSettings(BaseSettings):
        name: str = "Fonzie"
        last: int = 1984
        is_cool: bool = True


Disableable settings
--------------------

A bunch of settings are `disableable`, meaning that they can be turned off by the user. By convention, these settings
use an `enabled` flag, with a default to `true`, and the user can disable the whole setting dataclass by passing `false`
to it.

To set your setting class as disableable, just use the `DisableableBaseSettings` base class.

.. code-block:: python

    from harp.config import DisableableBaseSettings, settings_dataclass

    @settings_dataclass
    class AcmeSettings(DisableableBaseSettings):
        name: str = "Fonzie"
        last: int = 1984
        is_cool: bool = True


Lazy factories
--------------

Sometimes, your settings configure how some python objects will be instanciated. For this, you can use the lazy
factories:

.. code-block:: python

    from harp.config import BaseSettings, settings_dataclass, Lazy, Definition
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from acme import AbstractBroadcaster

    @settings_dataclass
    class AcmeSettings(BaseSettings):
        name: str = "Fonzie"
        last: int = 1984
        is_cool: bool = True

        broadcaster: Definition['AbstractBroadcaster'] = Lazy('acme:DefaultBroadcaster', channel="TF1")

You'll be able to build the broadcaster instance by calling `settings.broadcaster.build()`.


Adding default values
---------------------

.. todo:: cleanup and document that.


ApplicationSettingsMixin
------------------------

.. versionadded:: 0.10

All application settings classes should use the ``ApplicationSettingsMixin`` to provide standardized
enable/disable functionality. This mixin adds an ``enabled`` field (default: ``True``) that allows
applications to be toggled on/off via configuration.

.. code-block:: python

    from harp.config import ApplicationSettingsMixin, Configurable, Service

    # With Configurable base class
    class MyAppSettings(ApplicationSettingsMixin, Configurable):
        name: str = "MyApp"
        port: int = 8080

    # With Service base class
    class MyServiceSettings(ApplicationSettingsMixin, Service):
        endpoint: str = "http://api.example.com"
        timeout: int = 30

.. important::
   When using multiple inheritance, the ``ApplicationSettingsMixin`` **must** be listed first in the
   inheritance chain. This ensures the ``enabled`` field is properly initialized.

The ``enabled`` field allows users to disable applications without removing their configuration:

.. code-block:: yaml

    # config.yaml
    myapp:
        enabled: false  # Application will not be loaded
        name: "MyApp"
        port: 8080

.. note::
   Existing HARP applications are being migrated to use ``ApplicationSettingsMixin``. Until then,
   some applications may use ``extra="allow"`` to accept the ``enabled`` field.


Testing your Settings class
:::::::::::::::::::::::::::

It's quite easy to test your settings class, and you should do it once you know what they look like.

.. code-block:: python

    class TestAcmeSettings:
        def test_default_values(self):
            settings = AcmeSettings()
            assert settings.name == "Fonzie"
            assert settings.enabled is True  # Default from mixin

        def test_overriden_values(self):
            settings = AcmeSettings(name="Joe", enabled=False)
            assert settings.name == "Joe"
            assert settings.enabled is False

Of course this example is dumb, but you'll know what to do.


Using your settings
:::::::::::::::::::

In your `Application` sub-class, set the settings namespace and root settings type:

.. code-block:: python

    class AcmeApplication(Application):
        settings_namespace = "acme"
        settings_type = AcmeSettings

This will allow the base class to automatically bind the matching settings namespace, and as a result you'll get an
instance of your settings class as `self.settings` in your application.

The settings class is also registered with the dependency injection container, so you can auto inject it for your needs.

Configuration
=============

HARP leverages a powerful and composable configuration system to fit in any target environment and requirements.

Basically, HARP configuration is a big dictionary that is fed by various sources:

- YAML files
- Environment variables
- Command-line arguments

All sources can be combined, and can override each other. It means for example that you can have a reasonable default
configuration file, that you override with platform specific configuration file, that you override when run locally
with some command line arguments or environment.

If you're not familiar with it, you should read about `12-factor applications <https://12factor.net/>`_, which serves
as our guildeline to create a good and versatile configuration system (amongst other concepts).

:doc:`Read more about configuration in the Operations Guide </operate/configure/index>`

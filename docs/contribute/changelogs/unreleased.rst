Unreleased
==========


Changed
:::::::

* Core: configuration building and system instanciation was refactored and is now WAY simpler. As a result, the
  bootstrapping (internal) API has changed and there is no more "kernel factory" or complex "Config" object. Instead,
  we have a ConfigurationBuilder and a SystemBuilder that will expose a simple and understandable output api.
* Storage: removed unused storage "type" where the only valid value in the foreseeable future was "sqlalchemy".

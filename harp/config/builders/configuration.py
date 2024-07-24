import os
from typing import Iterable, Self, cast

import orjson
from config.common import ConfigurationBuilder as BaseConfigurationBuilder
from config.common import MapSource, merge_values
from config.env import EnvVars

from ...typing import GlobalSettings
from ..applications import ApplicationsRegistry
from ..defaults import DEFAULT_APPLICATIONS, DEFAULT_SYSTEM_CONFIG_FILENAMES
from ..examples import get_example_filename


def _get_system_configuration_sources():
    for _candidate in DEFAULT_SYSTEM_CONFIG_FILENAMES:
        if os.path.exists(_candidate):
            from config.yaml import YAMLFile

            yield YAMLFile(_candidate)
            break


class ConfigurationBuilder(BaseConfigurationBuilder):
    def __init__(
        self,
        default_values=None,
        /,
        *,
        use_default_applications=True,
        ApplicationsRegistryType=ApplicationsRegistry,
    ) -> None:
        self._defaults = default_values or {}
        self.applications = ApplicationsRegistryType()

        for app_name in self._defaults.pop("applications", []):
            self.applications.add(app_name)

        if use_default_applications:
            self.applications.add(*DEFAULT_APPLICATIONS)
        super().__init__()

    def add_file(self, filename: str):
        _, ext = os.path.splitext(filename)
        if ext in (".yaml", ".yml"):
            from config.yaml import YAMLFile

            self.add_source(YAMLFile(filename))
        elif ext in (".json",):
            from config.json import JSONFile

            self.add_source(JSONFile(filename))
        elif ext in (".ini", ".conf"):
            from config.ini import INIFile

            self.add_source(INIFile(filename))
        elif ext in (".toml",):
            from config.toml import TOMLFile

            self.add_source(TOMLFile(filename))
        else:
            raise ValueError(f"Unknown file extension: {ext}")

    def add_files(self, filenames: Iterable[str]):
        for filename in filenames or ():
            self.add_file(filename)

    def add_values(self, values: dict):
        for k, v in values.items():
            self.add_value(k, v)

    def normalize(self, x: dict):
        # todo: support recursive doted notation key. The easiest way would probably be to convert "a.b": ... into
        #  a: {b: ...}, meanwhile, let's be carfeul with those keys.
        return {
            k: (
                self.applications[k].Settings.normalize(v)
                if k in self.applications and hasattr(self.applications[k].Settings, "normalize")
                else v
            )
            for k, v in x.items()
        }

    def build(self) -> GlobalSettings:
        settings = {}
        for source in (
            EnvVars(prefix="DEFAULT__HARP_"),
            MapSource(self.applications.defaults()),
            MapSource(self._defaults or {}),
            *_get_system_configuration_sources(),
            *self._sources,
        ):
            merge_values(settings, self.normalize(source.get_values()))

        all_settings = (
            (name, self.applications.settings_for(name)(**settings.get(name, {})))
            for name, application in self.applications.items()
        )
        all_settings = list(all_settings)

        return cast(
            GlobalSettings,
            {
                "applications": self.applications.aslist(),
                **{name: value for name, value in sorted(all_settings) if value},
            },
        )

    @classmethod
    def from_commandline_options(cls, options) -> Self:
        # todo: config instead of sources in constructor ? for example no_default_apps, etc.
        builder = cls()

        # todo: raise if enabling AND disabling an app at the same time? maybe not but instructions should be taken in
        #  order, which looks hard to do using click...
        for _enabled_application in options.enable or ():
            builder.applications.add(_enabled_application)
        for _disabled_application in options.disable or ():
            builder.applications.remove(_disabled_application)

        builder.add_files((get_example_filename(example) for example in options.examples))
        builder.add_files(options.files or ())
        builder.add_source(EnvVars(prefix="HARP_"))
        builder.add_values(options.options or {})

        _endpoints = []
        for k, v in (options.endpoints or {}).items():
            _port, _url = v.split(":", 1)
            _endpoints.append({"name": k, "port": int(_port), "url": _url})
        if len(_endpoints):
            builder.add_value("proxy.endpoints", _endpoints)

        return builder

    @classmethod
    def from_bytes(cls, serialized: bytes, **kwargs) -> Self:
        unserialized = orjson.loads(serialized)
        return cls(unserialized, use_default_applications=False, **kwargs)

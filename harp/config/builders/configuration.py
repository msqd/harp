import os
from typing import Iterable, Self, cast

import orjson
from config.common import ConfigurationBuilder as BaseConfigurationBuilder
from config.common import MapSource, merge_values
from config.env import EnvVars

from harp.typing import GlobalSettings

from ..applications import ApplicationsRegistry
from ..defaults import DEFAULT_APPLICATIONS, DEFAULT_SYSTEM_CONFIG_FILENAMES
from ..examples import get_example_filename
from .system import System


def _get_system_configuration_sources():
    for _candidate in DEFAULT_SYSTEM_CONFIG_FILENAMES:
        if os.path.exists(_candidate):
            from config.yaml import YAMLFile

            yield YAMLFile(_candidate)
            break


class ConfigurationBuilder(BaseConfigurationBuilder):
    """
    A builder class for assembling the global configuration settings for HARP from various sources.

    This class extends config.ConfigurationBuilder, incorporating additional functionality specific to HARP,
    such as handling default applications and integrating with the ApplicationsRegistry. It supports adding
    configuration from files, environment variables, and direct values, with a focus on flexibility and ease of use.

    Attributes:
        _defaults (dict): Default values for the configuration, typically loaded from internal defaults or specified by the user.
        applications (ApplicationsRegistryType): An instance of ApplicationsRegistry or a subclass, managing the registration and configuration of HARP applications.

    Methods:
        add_file(filename: str): Adds a single configuration file by its filename.
        add_files(filenames: Iterable[str]): Adds multiple configuration files by their filenames.
        add_values(values: dict): Adds configuration values directly from a dictionary.
        normalize(x: dict): Normalizes the configuration values, potentially transforming them based on application-specific logic.
        build() -> GlobalSettings: Constructs the final, aggregated configuration settings as a GlobalSettings instance.
        from_commandline_options(options): Class method to create an instance of ConfigurationBuilder from command line options.
        from_bytes(serialized: bytes, **kwargs) -> Self: Class method to create an instance of ConfigurationBuilder from serialized bytes.

    The ConfigurationBuilder is central to the dynamic configuration system in HARP, allowing configurations to be built
    and modified in a flexible and intuitive manner.

    """

    def __init__(
        self,
        default_values=None,
        /,
        *,
        use_default_applications=True,
        ApplicationsRegistryType=ApplicationsRegistry,
    ) -> None:
        """
        Initializes a new instance of the ConfigurationBuilder.

        Parameters:
            default_values (dict, optional): A dictionary of default configuration values. Defaults to None.
            use_default_applications (bool, optional): Whether to automatically include default HARP applications in the configuration. Defaults to True.
            ApplicationsRegistryType (type, optional): The class to use for the applications registry. Defaults to ApplicationsRegistry.
        """
        self._defaults = default_values or {}
        self.applications = ApplicationsRegistryType()

        for app_name in self._defaults.pop("applications", []):
            self.applications.add(app_name)

        if use_default_applications:
            self.applications.add(*DEFAULT_APPLICATIONS)

        super().__init__()

    def add_file(self, filename: str):
        """
        Adds a configuration file to the builder.

        Parameters:
            filename (str): The path to the configuration file to add.

        Raises:
            ValueError: If the file extension is not recognized.
        """
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
        """
        Adds multiple configuration files to the builder.

        Parameters:
            filenames (Iterable[str]): An iterable of file paths to add.
        """
        for filename in filenames or ():
            self.add_file(filename)

    def add_values(self, values: dict):
        """
        Adds configuration values directly from a dictionary.

        Parameters:
            values (dict): A dictionary of configuration values to add.
        """
        # TODO: split first key on dots, with quote escaping, and create a recursive dict to apply correct merging.
        for k, v in values.items():
            self.add_value(k, v)

    def normalize(self, x: dict):
        """
        Normalizes the configuration values, potentially transforming them based on application-specific logic.

        Parameters:
            x (dict): The configuration values to normalize.

        Returns:
            dict: The normalized configuration values.
        """
        # todo: support recursive doted notation key. The easiest way would probably be to convert "a.b": ... into
        #  a: {b: ...}, meanwhile, let's be carfeul with those keys.
        return {k: (self.applications[k].normalize(v) if k in self.applications else v) for k, v in x.items()}

    def build(self) -> GlobalSettings:
        """
        Constructs the final, aggregated configuration settings as a GlobalSettings instance.

        Returns:
            GlobalSettings: The aggregated global settings derived from all added sources.
        """
        settings = {}
        for source in (
            EnvVars(prefix="DEFAULT__HARP_"),
            MapSource(self.applications.defaults()),
            MapSource(self._defaults or {}),
            *_get_system_configuration_sources(),
            *self._sources,
        ):
            merge_values(settings, self.normalize(source.get_values()))

        all_settings = []
        for name, application in self.applications.items():
            settings_type = self.applications[name].settings_type
            if not settings_type:
                continue
            _local_settings = settings.get(name, {})
            if not isinstance(_local_settings, settings_type):
                _local_settings = settings_type(**_local_settings)
            all_settings.append((name, _local_settings))

        return cast(
            GlobalSettings,
            {
                "applications": self.applications.aslist(),
                **{name: value for name, value in sorted(all_settings) if value},
            },
        )

    def __call__(self) -> GlobalSettings:
        return self.build()

    async def abuild_system(self) -> System:
        from .system import SystemBuilder

        return await SystemBuilder(self.applications, self.build).abuild()

    @classmethod
    def from_commandline_options(cls, options) -> Self:
        """
        Creates an instance of ConfigurationBuilder from command line options.

        Parameters:
            options: The command line options to use for building the configuration.

        Returns:
            ConfigurationBuilder: An instance of ConfigurationBuilder configured according to the provided command line options.
        """
        # todo: config instead of sources in constructor ? for example no_default_apps, etc.

        try:
            applications = options.applications
        except AttributeError:
            applications = None
        builder = cls(
            {"applications": applications} if applications else None,
            use_default_applications=not applications,
        )

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
        """
        Creates an instance of ConfigurationBuilder from serialized bytes.

        Parameters:
            serialized (bytes): The serialized configuration data.
            **kwargs: Additional keyword arguments to pass to the constructor.

        Returns:
            ConfigurationBuilder: An instance of ConfigurationBuilder initialized with the deserialized configuration data.
        """
        unserialized = orjson.loads(serialized)
        return cls(unserialized, use_default_applications=False, **kwargs)

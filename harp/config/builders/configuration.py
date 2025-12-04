import os
from typing import Iterable, Self, cast

import orjson
from config.common import ConfigurationBuilder as BaseConfigurationBuilder
from config.common import MapSource, merge_values
from config.env import EnvVars

from harp.typing import GlobalSettings
from harp.utils.config.yaml import include_constructor  # noqa

from harp import get_logger

from ..applications import ApplicationsRegistry
from ..defaults import DEFAULT_APPLICATIONS, DEFAULT_SYSTEM_CONFIG_FILENAMES
from ..examples import get_example_filename
from .system import System

logger = get_logger(__name__)


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
        applications_registry_type (type): The type of ApplicationsRegistry to use for managing applications.

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
        strict=False,
    ) -> None:
        """
        Initializes a new instance of the ConfigurationBuilder.

        Parameters:
            default_values (dict, optional): A dictionary of default configuration values. Defaults to None.
            use_default_applications (bool, optional): Whether to automatically include default HARP applications in the configuration. Defaults to True.
            strict (bool, optional): Whether to use strict validation mode. Defaults to False.
        """
        self._defaults = default_values or {}
        self.strict = strict
        self.applications = self.create_application_registry()
        self.applications_registry_type = type(self.applications)

        for app_name in self._defaults.pop("applications", []):
            self.applications.add(app_name)

        if use_default_applications:
            self.applications.add(*DEFAULT_APPLICATIONS)

        super().__init__()

    def create_application_registry(self):
        return ApplicationsRegistry()

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

    # System keys that are not application-specific
    SYSTEM_KEYS = frozenset({"applications", "harp_apps"})

    def _get_config_sources(self):
        """
        Get the list of configuration sources in priority order.

        Returns:
            tuple: Configuration sources to be processed.
        """
        return (
            EnvVars(prefix="DEFAULT__HARP_"),
            MapSource(self.applications.defaults()),
            MapSource(self._defaults or {}),
            *_get_system_configuration_sources(),
            *self._sources,
        )

    def _get_first_pass_config(self):
        """
        Performs a lightweight first pass of configuration parsing to detect application settings.

        Returns:
            dict: Raw configuration values from all sources.
        """
        settings = {}
        for source in self._get_config_sources():
            merge_values(settings, source.get_values())
        return settings

    def _filter_disabled_applications(self, settings: dict) -> list[str]:
        """
        Filter applications with enabled:false and log warnings.

        Args:
            settings: Configuration dictionary from first pass.

        Returns:
            list[str]: List of application names to remove from registry.
        """
        apps_to_remove = []
        for app_name in list(self.applications._applications.keys()):
            app_config = settings.get(app_name, {})

            # Check enabled flag from both dict and Pydantic model instances
            enabled = True
            if isinstance(app_config, dict):
                enabled = app_config.get("enabled", True)
            elif hasattr(app_config, "enabled"):
                enabled = app_config.enabled

            if enabled is False:
                apps_to_remove.append(app_name)
                logger.warning(
                    f"Application '{app_name}' is disabled as per configuration directive.",
                    app=app_name,
                )
        return apps_to_remove

    def _validate_unknown_applications(self, settings: dict, strict: bool, disabled_apps: list[str] = None):
        """
        Validate that all configured applications are loaded.

        Args:
            settings: Configuration dictionary from first pass.
            strict: If True, raise ValueError for unknown apps. If False, log warning.
            disabled_apps: List of apps that were explicitly disabled (skip validation for these).

        Raises:
            ValueError: If strict mode is enabled and unknown apps are configured.
        """
        disabled_apps = disabled_apps or []
        for key in settings:
            if (
                key not in self.applications
                and key not in self.SYSTEM_KEYS
                and key not in disabled_apps
                and isinstance(settings[key], dict)
            ):
                if strict:
                    raise ValueError(
                        f"Configuration found for application '{key}' which is not loaded. Running in strict mode, aborting."
                    )
                else:
                    logger.warning(
                        f"Configuration found for application '{key}' which is not loaded.",
                        app=key,
                        hint="Use --strict to enforce this as an error",
                    )

    def build(self, strict: bool = None) -> GlobalSettings:
        """
        Constructs the final, aggregated configuration settings as a GlobalSettings instance.

        This method performs a two-pass configuration build:
        1. First pass: Detect and filter applications with enabled:false
        2. Second pass: Build final configuration with filtered applications

        Parameters:
            strict (bool, optional): Override strict mode for this build. Uses instance strict if None.

        Returns:
            GlobalSettings: The aggregated global settings derived from all added sources.

        Raises:
            ValueError: If strict mode is enabled and configuration exists for unloaded applications.
        """
        if strict is None:
            strict = self.strict

        # First pass - detect disabled apps and validate unknown apps
        first_pass_settings = self._get_first_pass_config()

        # Filter disabled applications
        apps_to_remove = self._filter_disabled_applications(first_pass_settings)
        for app_name in apps_to_remove:
            self.applications.remove(app_name)

        # Validate unknown applications (skip disabled apps)
        self._validate_unknown_applications(first_pass_settings, strict, disabled_apps=apps_to_remove)

        # Second pass - build final configuration with normalized settings
        settings = {}
        for source in self._get_config_sources():
            merge_values(settings, self.normalize(source.get_values()))

        all_settings = []
        for name, application in self.applications.items():
            settings_type = self.applications[name].settings_type
            if not settings_type:
                continue
            _local_settings = settings.get(name.rsplit(".", 1)[-1], {})
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

    def get_filtered_applications_registry(self):
        """
        Returns the applications registry after filtering disabled apps.
        This requires calling build() first to apply filtering.
        """
        return self.applications

    async def abuild_system(self, *, validate_dependencies: bool = True) -> System:
        """Build the system with optional dependency validation.

        Args:
            validate_dependencies: If True, validate and resolve application dependencies.
                                  Set to False in tests when building partial systems. Default: True.

        Returns:
            System: The built system instance.
        """
        from .system import SystemBuilder

        return await SystemBuilder(self.applications, self.build).abuild(validate_dependencies=validate_dependencies)

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

        # Get strict flag if available
        try:
            strict = options.strict
        except AttributeError:
            strict = False

        builder = cls(
            {"applications": applications} if applications else None,
            use_default_applications=not applications,
            strict=strict,
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

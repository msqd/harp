"""
Factory configuration, does nothing but can be used to instanciate a server.
"""

import importlib.util
import os
import pprint
from copy import deepcopy
from types import MappingProxyType
from typing import Self, Type

import orjson
from config.ini import INIFile
from config.json import JSONFile
from config.toml import TOMLFile
from rodi import Container
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.commandline.server import CommonServerOptions
from harp.config.application import Application
from harp.utils.identifiers import is_valid_dotted_identifier

logger = get_logger(__name__)


def get_application_class_name(name):
    return "".join(map(lambda x: x.title().replace("_", ""), name.rsplit(".", 1)[-1:])) + "Application"


def _resolve_application_aliases(spec):
    if "." not in spec:
        _candidate = ".".join(("harp_apps", spec))
        if importlib.util.find_spec(_candidate):
            return _candidate
    return spec


class Config:
    DEFAULT_APPLICATIONS = [
        "harp_apps.http_client",
        "harp_apps.proxy",
        "harp_apps.dashboard",
        "harp_apps.sqlalchemy_storage",
        "harp_apps.telemetry",
        "harp_apps.janitor",
        "harp_apps.contrib.sentry",  # todo: allow to extend application list in config file without overriding all
    ]

    def __init__(self, settings=None, /, applications=None):
        self._raw_settings = {"applications": applications or []} | (settings or {})
        self._validated_settings = None
        self._debug_applications = set()
        self._application_types = {}
        self._applications = []
        self._disabled_applications = set()

    def __eq__(self, other: Self):
        return self.settings == other.settings

    def __repr__(self):
        return (
            f"<{type(self).__name__}{'' if self._validated_settings else '*'} "
            f"settings={orjson.dumps(self.settings.copy()).decode()}>"
        )

    @property
    def settings(self):
        if self._validated_settings is not None:
            return self._validated_settings
        return self._raw_settings

    @property
    def applications(self):
        if not self._validated_settings:
            raise RuntimeError("Configuration not validated.")
        return self._validated_settings.get("applications", [])

    def reset(self):
        self._validated_settings = None

    def add_defaults(self):
        for application in type(self).DEFAULT_APPLICATIONS:
            self.add_application(application)

    def set(self, key, value):
        if not is_valid_dotted_identifier(key):
            raise ValueError(f"Invalid settings key: {key}")

        self.reset()

        bits: list[str] = key.split(".")
        current = self._raw_settings
        for bit in bits[:-1]:
            current = current.setdefault(bit, {})
        current[bits[-1]] = value

    def add_application(self, name, /, *, debug=False):
        if not is_valid_dotted_identifier(name):
            raise ValueError(f"Invalid application name: {name}")
        self.reset()
        name = _resolve_application_aliases(name)
        if name not in self._raw_settings["applications"]:
            self._raw_settings["applications"].append(name)
            if debug:
                self._debug_applications.add(name)

    def remove_application(self, name):
        if not is_valid_dotted_identifier(name):
            raise ValueError(f"Invalid application name: {name}")
        self.reset()
        name = _resolve_application_aliases(name)
        if name in self._raw_settings["applications"]:
            self._raw_settings["applications"].remove(name)
        self._debug_applications.discard(name)

    def read_env(self, options: CommonServerOptions, /):
        """
        Parses sys.argv-like arguments.

        :param args:
        :param files: list of filenames to load in order. Will happen after defaults env and files.
        :return: argparse.Namespace

        """
        for _enabled_application in options.enable or ():
            self.add_application(_enabled_application)
        for _disabled_application in options.disable or ():
            self.remove_application(_disabled_application)

        from config.common import ConfigurationBuilder, MapSource
        from config.env import EnvVars
        from config.yaml import YAMLFile

        builder = ConfigurationBuilder()

        # default config
        builder.add_source(MapSource({}))
        builder.add_source(EnvVars(prefix="DEFAULT__HARP_"))

        # current
        builder.add_source(MapSource(self._raw_settings))

        # load default system config (if present)
        if os.path.exists("/etc/harp.yaml"):
            builder.add_source(YAMLFile("/etc/harp.yaml"))
        elif os.path.exists("/etc/harp.yml"):
            builder.add_source(YAMLFile("/etc/harp.yml"))

        # load user config
        for file in options.files or ():
            _, ext = os.path.splitext(file)
            if ext in (".yaml", ".yml"):
                builder.add_source(YAMLFile(file))
            elif ext in (".json",):
                builder.add_source(JSONFile(file))
            elif ext in (".ini", ".conf"):
                builder.add_source(INIFile(file))
            elif ext in (".toml",):
                builder.add_source(TOMLFile(file))
            else:
                raise ValueError(f"Unknown file extension: {ext}")

        builder.add_source(EnvVars(prefix="HARP_"))

        for k, v in (options.options or {}).items():
            builder.add_value(k, v)

        # reset option
        if options.reset:
            builder.add_value("storage.drop_tables", True)

        self._raw_settings = builder.build().values

        self._raw_settings.setdefault("proxy", {})
        self._raw_settings["proxy"].setdefault("endpoints", [])

        for k, v in (options.endpoints or {}).items():
            _port, _url = v.split(":", 1)
            self._raw_settings["proxy"]["endpoints"].append(
                {
                    "name": k,
                    "port": int(_port),
                    "url": _url,
                }
            )

    def validate(self, *, allow_extraneous_settings=False):
        if self._validated_settings is None:
            to_be_validated = deepcopy(self._raw_settings)
            application_names = to_be_validated.pop("applications", [])
            validated = {"applications": []}

            # round 1: import applications and set defaults before validation
            application_types, to_be_validated = self._validate_round_1_import_applications(
                application_names, to_be_validated
            )
            for application in application_types:
                validated["applications"].append(application.name)

            applications, newly_validated = self._validate_round_2_extract_and_validate_settings(
                application_types, to_be_validated
            )
            newly_validated.pop("applications", None)  # not allowed xxx todo raise
            validated |= newly_validated

            if to_be_validated != {} and not allow_extraneous_settings:
                logger.warning(f"Unknown settings remaining: {to_be_validated}")

            # propagate for the world to use
            self._validated_settings = MappingProxyType(validated)
            self._applications = applications

        logger.debug(f"Configuration validated: {pprint.pformat(self._validated_settings)}")

        return self._validated_settings

    def get_application_type(self, name: str) -> Type[Application]:
        if name not in self._application_types:
            application_spec = importlib.util.find_spec(name)
            if not application_spec:
                raise ValueError(f'Unable to find application "{name}".')

            try:
                application_module = __import__(".".join((application_spec.name, "__app__")), fromlist=["*"])
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    f'A python package for application "{name}" was found but it is not a valid harp application. '
                    'Did you forget to add an "__app__.py"?'
                ) from exc

            application_class_name = get_application_class_name(name)
            if not hasattr(application_module, application_class_name):
                raise AttributeError(
                    f'Application module for {name} does not contain a "{application_class_name}" class.'
                )

            self._application_types[application_spec.name] = getattr(application_module, application_class_name)
            self._application_types[application_spec.name].name = application_spec.name

        if name not in self._application_types:
            raise RuntimeError(f'Unable to load application "{name}", application class definition not found.')

        return self._application_types[name]

    def _validate_round_1_import_applications(self, names, to_be_validated):
        # note: to_be_validated is modified in place (is this right ?), but still returned to avoid confusion
        if len(self._debug_applications):
            print("DEBUG: Configuration > Round 1 (import applications) > START")

        types = []

        for _name in names:
            _type = self.get_application_type(_name)

            if _type.settings_namespace:
                _settings = to_be_validated.get(_type.settings_namespace, None)
                if (_defaults := _type.defaults(deepcopy(_settings) if _settings else None)) is not None:
                    to_be_validated[_type.settings_namespace] = _defaults
            else:
                pass  # todo assert application explicitely opted in for no defaults ?

            if _type.name in self._debug_applications:
                print(f"DEBUG: {_type}::set_default_settings(...)")

            types.append(_type)

        if len(self._debug_applications):
            print("DEBUG: Configuration > Round 1 (import applications) > END")
            print(f"DEBUG: to_be_validated={pprint.pformat(to_be_validated)}")

        return types, to_be_validated

    def _validate_round_2_extract_and_validate_settings(self, application_types, to_be_validated):
        applications = []
        validated = {}
        # round 2: validate and extract settings
        if len(self._debug_applications):
            print("DEBUG: Configuration > Round 2 > START")
        for application_type in application_types:
            if application_type.settings_namespace:
                if not application_type.supports(to_be_validated.get(application_type.settings_namespace, {})):
                    raise ValueError(
                        f'Application "{application_type.name}" is not configurable with the current configuration.'
                    )
                application_settings = to_be_validated.pop(application_type.settings_namespace, None)
                if application_type.settings_type:
                    application_settings = application_type.settings_type(**application_settings)
            else:
                application_settings = None

            if application_type.name in self._debug_applications:
                print(f"DEBUG: {application_type}::extract_settings() -> {application_settings}")

            if application_settings is None and application_type.settings_namespace is not None:
                raise ValueError(
                    f'Application "{application_type.name}" is not configurable with the current configuration '
                    f"(expected some configuration, got none)."
                )

            application = application_type(application_settings)
            application_validated_settings = application.validate()
            if application_type.settings_namespace:
                validated |= {application_type.settings_namespace: application_validated_settings}
            applications.append(application)

        if len(self._debug_applications):
            print("DEBUG: Configuration > Round 2 > END")
        return applications, validated

    def register_events(self, dispatcher: IAsyncEventDispatcher):
        self.validate()
        for application in self._applications:
            application.register_events(dispatcher)

    def register_services(self, container: Container):
        self.validate()
        for application in self._applications:
            application.register_services(container)

    def serialize(self):
        self.validate()
        return orjson.dumps(self.settings.copy())

    @classmethod
    def deserialize(cls, settings):
        return cls(orjson.loads(settings))

import glob
import inspect
import os.path
from os.path import dirname
from pkgutil import iter_modules

import pytest
from pydantic import BaseModel, ValidationError

from harp import ROOT_DIR
from harp.config import Stateful
from harp.config.asdict import asdict
from harp.utils.config import yaml
from harp.utils.packages import get_full_qualified_name


def list_submodules(module):
    try:
        modpath = module.__path__
    except AttributeError:
        # not a package, return empty list
        return []

    submodules = []
    for submodule in iter_modules(modpath):
        submodules.append(submodule.name)
    return submodules


all_apps = [
    ".".join(dirname(x).split(os.path.sep)) for x in glob.glob("**/__app__.py", root_dir=ROOT_DIR, recursive=True)
]


def get_all_settings_classes(modname):
    modpath, modattr = modname.rsplit(".", 1)
    module = __import__(modname, fromlist=[modattr])
    for _name, _impl in inspect.getmembers(module, inspect.isclass):
        if not _impl.__module__.startswith(modpath):
            continue
        for submodname in list_submodules(module):
            yield from get_all_settings_classes(f"{modname}.{submodname}")
        yield _name, _impl


# Some settings classes requires some value to have a meaning. They are not usually the root settings but some
# subsettings that does not really make sense unless relevant configuration is passed. In that case, we provide the
# minimal set of settings required to instanciate it.
REQUIRED_SETTINGS = {
    "harp_apps.proxy.settings.endpoint.BaseEndpointSettings": {
        "name": "api",
        "port": 4000,
    },
    "harp_apps.proxy.settings.remote.endpoint.RemoteEndpointSettings": {
        "url": "https://www.example.com/",
    },
    "harp_apps.dashboard.settings.auth.User": {
        "password": "secret",
    },
}

REQUIRED_SETTINGS["harp_apps.proxy.settings.endpoint.EndpointSettings"] = REQUIRED_SETTINGS[
    "harp_apps.proxy.settings.endpoint.BaseEndpointSettings"
]
IGNORE_TYPES = {
    "harp_apps.proxy.settings.liveness.base.BaseLiveness",
}


@pytest.mark.parametrize("app", all_apps)
def test_all_applications_default_settings(app, snapshot):
    modname = app.rsplit(".", 1)[-1]
    submodules = list_submodules(__import__(app, fromlist=[modname]))
    if "settings" not in submodules:
        pytest.skip(f"No settings submodule found in {app}.")

    _types = _get_all_configurable_types_for_application(app)

    all_defaults = {}
    for _fullname, (_name, _type) in _types.items():
        _kwargs: dict = REQUIRED_SETTINGS.get(_fullname, {})

        if not issubclass(_type, BaseModel):
            continue

        if get_full_qualified_name(_type) in IGNORE_TYPES:
            continue

        if issubclass(_type, Stateful):
            _settings_type = _type.get_settings_type()
            _kwargs["settings"] = REQUIRED_SETTINGS.get(get_full_qualified_name(_settings_type), {})

        if _fullname in REQUIRED_SETTINGS:
            with pytest.raises(ValidationError):
                _type()

        instance = _type(**_kwargs)

        all_defaults[_fullname] = yaml.dump(asdict(instance))

    assert all_defaults == snapshot


def _get_all_configurable_types_for_application(app):
    all_settings_classes = {}
    for _name, _type in get_all_settings_classes(app + ".settings"):
        _fullname = f"{_type.__module__}.{_type.__qualname__}"
        if _fullname not in all_settings_classes:
            all_settings_classes[_fullname] = _name, _type
    return all_settings_classes

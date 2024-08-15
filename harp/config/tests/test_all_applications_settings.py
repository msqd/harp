import glob
import inspect
import os.path
from os.path import dirname
from pkgutil import iter_modules

import pytest
from pydantic import ValidationError

from harp import ROOT_DIR
from harp.config import asdict
from harp.utils.config import yaml


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


# Some settings classes requires some value to have a maening. They are not usually the root settings but some
# subsettings that does not really make sense unless relevant configuration is passed. In that case, we provide the
# minimal set of settings required to instanciate it.
REQUIRED_SETTINGS = {
    "harp_apps.proxy.settings.endpoint.EndpointSettings": {
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


@pytest.mark.parametrize("app", all_apps)
def test_all_applications_default_settings(app, snapshot):
    modname = app.rsplit(".", 1)[-1]
    submodules = list_submodules(__import__(app, fromlist=[modname]))
    if "settings" not in submodules:
        pytest.skip(f"No settings submodule found in {app}.")

    all_settings_classes = {}
    for _name, _impl in get_all_settings_classes(app + ".settings"):
        _fullname = f"{_impl.__module__}.{_impl.__qualname__}"
        if _fullname not in all_settings_classes:
            all_settings_classes[_fullname] = _name, _impl

    all_defaults = {}
    for _fullname, (_name, _impl) in all_settings_classes.items():
        if _fullname in REQUIRED_SETTINGS:
            with pytest.raises(ValidationError):
                _impl()
            settings_with_defaults = _impl(**REQUIRED_SETTINGS[_fullname])
        else:
            try:
                settings_with_defaults = _impl()
            except ValidationError as exc:
                raise ValueError(f"Invalid default settings for {_fullname}") from exc
        all_defaults[_fullname] = yaml.dump(asdict(settings_with_defaults))

    assert all_defaults == snapshot

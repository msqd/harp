from importlib.machinery import ModuleSpec
from types import ModuleType
from unittest.mock import patch

import orjson

from harp.config import Application, ApplicationsRegistry, ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.identifiers import is_valid_dotted_identifier


def test_is_valid_extension_name():
    # empty
    assert not is_valid_dotted_identifier("")

    # usual
    assert is_valid_dotted_identifier("foo.bar")
    assert is_valid_dotted_identifier("toto")

    # empty part
    assert not is_valid_dotted_identifier(".foo")
    assert not is_valid_dotted_identifier("foo..bar")
    assert not is_valid_dotted_identifier("bar.")

    # dashed/underscored
    assert is_valid_dotted_identifier("o_o")
    assert not is_valid_dotted_identifier("o-o")
    assert is_valid_dotted_identifier("_mazette")
    assert is_valid_dotted_identifier("raise_")


class ApplicationsRegistryMock(ApplicationsRegistry):
    def add_mock(self, name, impl):
        self._applications[name] = impl


def test_add_application(snapshot):
    builder = ConfigurationBuilder(use_default_applications=False)
    builder.applications.add("storage")

    assert len(builder.applications) == 1

    settings = builder()

    serialized = orjson.dumps(asdict(settings))
    assert serialized == snapshot

    new_builder = ConfigurationBuilder.from_bytes(serialized, ApplicationsRegistryType=ApplicationsRegistryMock)
    assert asdict(new_builder()) == asdict(settings)

    module = ModuleType("foo.bar")
    module.__spec__ = ModuleSpec(name="foo.bar", loader=None)

    app_module = ModuleType("foo.bar.__app__")
    app_module.application = Application()
    app_module.__spec__ = ModuleSpec(name="foo.bar.__app__", loader=None)

    with patch.dict("sys.modules", {"foo.bar": module, "foo.bar.__app__": app_module}):
        new_builder.applications.add("foo.bar")
        new_settings = new_builder()

    assert asdict(new_settings) != asdict(settings)

    assert asdict(new_settings) == snapshot
    assert orjson.dumps(asdict(new_settings)) == snapshot

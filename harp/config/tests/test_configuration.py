import orjson

from harp.config import Application, ApplicationsRegistry, ConfigurationBuilder, asdict
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
    assert builder.applications["storage"].__module__ == "harp_apps.storage.__app__"

    settings = builder.build()

    serialized = orjson.dumps(asdict(settings))
    assert serialized == snapshot

    new_builder = ConfigurationBuilder.from_bytes(serialized, ApplicationsRegistryType=ApplicationsRegistryMock)
    assert asdict(new_builder.build()) == asdict(settings)

    new_builder.applications.add_mock("foo.bar", type("MockedApplication", (Application,), {"name": "foo.bar"}))

    new_settings = new_builder.build()
    assert asdict(new_settings) != asdict(settings)

    assert asdict(new_settings) == snapshot
    assert orjson.dumps(asdict(new_settings)) == snapshot

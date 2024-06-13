from harp import Config
from harp.config.application import Application
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


def test_add_application():
    config = Config()
    config.add_application("harp_apps.sqlalchemy_storage")

    assert config.settings == {
        "applications": ["harp_apps.sqlalchemy_storage"],
    }

    # can we serialize it?
    serialized = config.serialize()

    assert serialized == (
        b'{"applications":["harp_apps.sqlalchemy_storage"],"storage":{"type":"sqlalche'
        b'my","url":"sqlite+aiosqlite:///:memory:","migrate":true}}'
    )

    # is the unserialized result the same as before serialization?
    new_config = Config.deserialize(serialized)
    assert new_config == config

    new_config.add_application("foo.bar")

    # Try adding twice
    new_config.add_application("foo.bar")
    assert new_config != config
    assert new_config.settings == {
        "applications": ["harp_apps.sqlalchemy_storage", "foo.bar"],
        "storage": {"migrate": True, "type": "sqlalchemy", "url": "sqlite+aiosqlite:///:memory:"},
    }

    new_config._application_types["foo.bar"] = type("MockedExtension", (Application,), {"name": "foo.bar"})

    assert new_config.serialize() == (
        b'{"applications":["harp_apps.sqlalchemy_storage","foo.bar"],"storage":{"type"'
        b':"sqlalchemy","url":"sqlite+aiosqlite:///:memory:","migrate":tr'
        b"ue}}"
    )

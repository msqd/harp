from typing import Generic, Type, TypeVar

from harp.config.asdict import asdict
from harp.config.configurables.base import BaseConfigurable

TConfigurable = TypeVar("TConfigurable", bound=BaseConfigurable)


class BaseConfigurableTest(Generic[TConfigurable]):
    type: Type[TConfigurable]
    initial = {}
    expected = {}
    expected_verbose = {}

    def create(self, **kwargs) -> TConfigurable:
        return self.type.from_kwargs(**{**self.initial, **kwargs})

    def test_defaults(self):
        obj = self.create()
        assert asdict(obj) == self.expected

    def test_defaults_verbose(self):
        obj = self.create()
        assert asdict(obj, verbose=True) == self.expected_verbose

    def test_jsonschema_for_validation(self, snapshot):
        schema = self.type.model_json_schema(mode="validation")
        schema.pop("description", None)
        assert schema == snapshot

    def test_jsonschema_for_serialization(self, snapshot):
        schema = self.type.model_json_schema(mode="serialization")
        schema.pop("description", None)
        assert schema == snapshot

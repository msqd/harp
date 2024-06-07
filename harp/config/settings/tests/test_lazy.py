from dataclasses import dataclass
from decimal import Decimal

import pytest
from hishel import Controller

from harp.config import BaseSetting, Definition, Lazy, asdict


class TestFactoryDefinition:
    def test_not_existing(self):
        definition = Lazy("foo:bar")
        assert isinstance(definition, Definition)

        assert definition.path == "foo"
        assert definition.name == "bar"
        assert len(definition.args) == 0
        assert len(definition.kwargs) == 0

        with pytest.raises(ImportError):
            assert definition.validate()

    def test_existing(self):
        definition = Lazy("harp.config:Application", {"foo": "bar"})
        assert isinstance(definition, Definition)

        assert definition.path == "harp.config"
        assert definition.name == "Application"
        assert len(definition.args) == 1
        assert len(definition.kwargs) == 0

        assert definition.validate()

        instance = definition.build()
        assert instance.settings == {"foo": "bar"}

    def test_using_type(self):
        definition = Lazy(Decimal)
        assert isinstance(definition, Definition)

        assert definition.path == "decimal"
        assert definition.name == "Decimal"

        assert definition.build("42.0") == 42

    def test_usage(self):
        @dataclass(kw_only=True)
        class MySetting:
            dep: Definition[Decimal] = Lazy("decimal:Decimal")

            def __post_init__(self):
                self.dep = Lazy(self.dep)

        setting = MySetting()
        assert setting.dep.build() == 0

        class OtherDecimal(Decimal):
            pass

        setting = MySetting(dep=OtherDecimal)
        assert setting.dep.build() == 0

        setting = MySetting(dep="decimal:Decimal")
        assert setting.dep.build() == 0

        setting = MySetting(dep={"@type": "decimal:Decimal"})
        assert setting.dep.build() == 0

        setting = MySetting(dep={"@type": "decimal:Decimal", "@args": ["42.0"]})
        assert setting.dep.build() == 42

    def test_reallife(self):
        @dataclass(kw_only=True)
        class MySetting:
            dep: Definition[Controller] = Lazy("hishel:Controller")

            def __post_init__(self):
                self.dep = Lazy(self.dep)

        setting = MySetting()
        assert setting.dep.build()._force_cache is False

        class MyController(Controller):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._force_cache = True

        setting = MySetting(dep={"@type": MyController})
        assert setting.dep.build()._force_cache is True

    def test_serialize(self):
        @dataclass
        class Foo(BaseSetting):
            dep: Definition = Lazy("decimal:Decimal")

        assert asdict(Foo()) == {
            "dep": {
                "@type": "decimal:Decimal",
            }
        }

        assert asdict(
            Foo(
                dep="io:StringIO",
            )
        ) == {
            "dep": {
                "@type": "io:StringIO",
            }
        }

        assert asdict(
            Foo(
                dep={"@type": "io:StringIO"},
            )
        ) == {
            "dep": {
                "@type": "io:StringIO",
            }
        }

        assert asdict(
            Foo(
                dep={"@type": "math:gcd", "@args": [10, 20, 30]},
            )
        ) == {
            "dep": {
                "@type": "math:gcd",
                "@args": (10, 20, 30),
            }
        }

        assert asdict(
            Foo(
                dep={"@type": "foo:bar", "@args": [1, 2, 3, 5, 8], "algorithm": "fibonacci"},
            )
        ) == {
            "dep": {
                "@args": (1, 2, 3, 5, 8),
                "@type": "foo:bar",
                "algorithm": "fibonacci",
            },
        }

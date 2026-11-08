import sys
from argparse import Namespace
from contextlib import contextmanager
from os.path import basename, dirname, join
from string import Template
from tempfile import NamedTemporaryFile
from types import ModuleType

import pytest

from harp.services import CircularDependencyException, Container
from harp.utils.packages import get_full_qualified_name


class Stub:
    pass


class AnotherStub:
    pass


base_content = f'services: [ {{ name: "foo", type: "{get_full_qualified_name(Stub)}" }} ]'


@contextmanager
def _create_temporary_configuration_files(template: Template):
    with (
        NamedTemporaryFile(delete_on_close=False, suffix=".yaml") as base,
        NamedTemporaryFile(delete_on_close=False, suffix=".yaml") as child,
    ):
        base.write(base_content.encode())
        base.close()
        child.write(template.substitute(filename=base.name, basename=basename(base.name)).encode())
        child.close()
        yield Namespace(base=base, child=child)


def test_container_load_include():
    with _create_temporary_configuration_files(Template("services: [ !include $filename ]")) as files:
        container = Container()
        container.load(files.child.name, bind_settings={})
        provider = container.build_provider()
        assert isinstance(provider.get("foo"), Stub)


def test_container_load_include_override():
    with _create_temporary_configuration_files(
        Template(
            f'services: [ !include $filename, {{ name: "foo", override: "replace", type: "{get_full_qualified_name(AnotherStub)}" }} ]'
        )
    ) as files:
        container = Container()
        container.load(files.child.name, bind_settings={})
        provider = container.build_provider()
        assert isinstance(provider.get("foo"), AnotherStub)


def test_container_load_include_from_module():
    m = ModuleType("foo")
    sys.modules[m.__name__] = m

    with _create_temporary_configuration_files(
        Template(f'services: [ !include "$basename from {m.__name__}" ]')
    ) as files:
        m.__file__ = join(dirname(files.child.name), "__init__.py")
        m.__path__ = [dirname(files.child.name)]

        container = Container()
        container.load(files.child.name, bind_settings={})
        provider = container.build_provider()
        instance = provider.get("foo")

        assert isinstance(instance, Stub)


def test_container_build_reports_circular_references(tmp_path):
    services = tmp_path / "services.yml"
    services.write_text(
        "services:\n"
        "  - {name: a, type: collections.OrderedDict, arguments: {other: !ref b}}\n"
        "  - {name: b, type: collections.UserDict, arguments: {other: !ref a}}\n"
    )
    container = Container()
    container.load(str(services), bind_settings={})

    with pytest.raises(CircularDependencyException):
        container.build_provider()

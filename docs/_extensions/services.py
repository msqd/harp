import logging
from functools import cached_property
from typing import Any, ClassVar

import orjson
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.misc import adapt_path
from sphinx.domains.python import PyClasslike
from sphinx.ext.autodoc import Documenter, ObjectMember, identity
from sphinx.util.typing import OptionSpec

from harp.services.models import ServiceDefinition, ServiceDefinitionCollection
from harp.utils.config import yaml

logger = logging.getLogger(__name__)


class PartialSettings(dict):
    def __getitem__(self, item):
        if item in self:
            return self.get(item)
        if "." in item:
            parts = item.split(".")
            current = self
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return None
            return current
        return super().get(item)


class PyService(PyClasslike):
    pass


class PyServices(PyClasslike):
    pass


_REGISTRY = {}


class ServiceCollectionDocumenter(Documenter):
    objtype = "services"
    directivetype = "services"
    content_indent = ""
    _extra_indent = "   "

    option_spec: ClassVar[OptionSpec] = {
        "file": identity,
        "namespace": identity,
        "settings": directives.unchanged,
    }

    @cached_property
    def settings(self):
        return orjson.loads(self.options.get("settings", "{}"))

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        coll_id = str(id(self.object))
        if coll_id not in _REGISTRY:
            _REGISTRY[coll_id] = self.object
        members = []
        for service in self.object:
            members.append(ObjectMember(coll_id + "/" + service.name, service))
        return True, members

    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str) -> tuple[str | None, list[str]]:
        return (path or "") + base, []

    @classmethod
    def can_document_member(cls: type[Documenter], member: Any, membername: str, isattr: bool, parent: Any) -> bool:
        try:
            return isinstance(member, ServiceDefinitionCollection)
        except TypeError:
            return False

    def import_object(self, raiseerror: bool = False) -> bool:
        filename = adapt_path(self.options.get("file"), self.env.docname, self.env.srcdir)
        collection = ServiceDefinitionCollection.model_validate_yaml(filename)
        collection.bind_settings(PartialSettings(self.settings))
        self.object = collection
        return True

    def add_directive_header(self, sig: str) -> None:
        self.add_line(".. code:: yaml", "<autodoc>")
        self.add_empty_line()
        old_indent = self.indent
        self.indent += self._extra_indent
        settings = self.settings
        if namespace := self.options.get("namespace"):
            settings = {namespace: settings}
        self.add_line(yaml.dump(settings), "<autodoc>")
        self.indent = old_indent

    def add_empty_line(self):
        self.add_line("   ", "<autodoc>")

    def filter_members(
        self,
        members: list[ObjectMember],
        want_all: bool,
    ) -> list[tuple[str, Any, bool]]:
        ret = []
        for obj in members:
            membername = obj.__name__
            member = obj.object
            ret.append((membername, member, False))
        return ret


class ServiceDocumenter(Documenter):
    objtype = "service"
    directivetype = "service"

    priority = 15

    option_spec: ClassVar[OptionSpec] = {
        "file": identity,
    }

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        return True, []

    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str) -> tuple[str | None, list[str]]:
        return (path or "") + base, []

    def parse_name(self) -> bool:
        return True

    @classmethod
    def can_document_member(cls: type[Documenter], member: Any, membername: str, isattr: bool, parent: Any) -> bool:
        try:
            return isinstance(member, ServiceDefinition)
        except TypeError:
            return False

    def add_directive_header(self, sig: str) -> None:
        # Add the directive header for the service
        self.add_line(f".. py:service:: {sig}", "<autodoc>")

    def add_empty_line(self):
        self.add_line("   ", "<autodoc>")

    def add_content(self, more_content: Any, no_docstring: bool = False) -> None:
        self.add_empty_line()

        if self.object.base != (self.object.type or self.object.base):
            self.add_line(f"Base: :class:`{self.object.base}`", "<autodoc>")
            self.add_empty_line()

        if self.object.description:
            self.add_line(self.object.description, "<autodoc>")
            self.add_empty_line()

        for _name, _value in ((self.object.defaults or {}) | (self.object.arguments or {})).items():
            self.add_line(f".. attribute:: {_name}", "<autodoc>")
            self.add_line(f"   :type: {type(_value).__name__}", "<autodoc>")
            self.add_line(f"   :value: {repr(_value)}", "<autodoc>")

    def import_object(self, raiseerror: bool = False) -> bool:
        pkgname, _, serviceid = self.name.partition("::")
        collid, _, servicename = serviceid.partition("/")
        if collid in _REGISTRY:
            for service in _REGISTRY[collid]:
                if service.name == servicename:
                    self.object = service
                    return True

        filename = adapt_path(self.options.get("file"), self.env.docname, self.env.srcdir)
        collection = ServiceDefinitionCollection.model_validate_yaml(filename)
        collection.bind_settings(PartialSettings({}))
        for service in collection:
            if service.name == self.name:
                self.object = service
                return True
        return False

    def format_signature(self) -> str:
        return f"{self.object.name}() -> {self.object.type or self.object.base}"

    def generate(
        self,
        more_content: Any | None = None,
        real_modname: str | None = None,
        check_module: bool = False,
        all_members: bool = False,
    ) -> None:
        if not self.parse_name():
            # need a module to import
            logger.warning(
                "don't know which module to import for autodocumenting "
                '%r (try placing a "module" or "currentmodule" directive '
                "in the document, or giving an explicit module name)",
                self.name,
            )
            return

        # now, import the module and get object to document
        if not self.import_object():
            return

        sourcename = self.get_sourcename()

        # make sure that the result starts with an empty line.  This is
        # necessary for some situations where another directive preprocesses
        # reST and no starting newline is present
        self.add_line("", sourcename)

        # format the object's signature, if any
        try:
            sig = self.format_signature()
        except Exception as exc:
            logger.warning("error while formatting signature for %s: %s", self.fullname, exc)
            return

        # generate the directive header and options, if applicable
        self.add_directive_header(sig)
        self.add_line("", sourcename)

        # e.g. the module directive doesn't have content
        self.indent += self.content_indent

        # add all content (from docstrings, attribute docs etc.)
        self.add_content(more_content)

        # document members, if possible
        self.document_members(all_members)


def setup(app):
    app.add_directive_to_domain("py", "service", PyService)
    app.add_directive_to_domain("py", "services", PyServices)
    app.add_autodocumenter(ServiceDocumenter)
    app.add_autodocumenter(ServiceCollectionDocumenter)
    return {
        "version": "0.2",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

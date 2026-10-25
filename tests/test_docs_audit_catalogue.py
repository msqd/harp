"""
The operating page lists the audit events and the loggable events. It is checked against the declared event classes, so
a new event cannot ship undocumented, nor can the page keep one that no longer exists.
"""

import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import harp_apps
from harp.unit_of_work import loggable_events
from harp.unit_of_work.audit import AuditableEvent

PAGE = Path(__file__).parent.parent / "docs" / "operate" / "audit.rst"
SECTION = re.compile(r"^(?P<title>[^\n]+)\n:{3,}\n(?P<body>.*?)(?=^[^\n]+\n:{3,}\n|\Z)", re.MULTILINE | re.DOTALL)
ENTRY = re.compile(r"^``(?P<id>[\w.]+)``\n(?P<body>(?:(?: {4}.*)?\n)+)", re.MULTILINE)


def _import_declared_events():
    """Events are declared in the ``events`` modules of the applications; importing them registers the classes."""
    for module in pkgutil.walk_packages(harp_apps.__path__, "harp_apps."):
        if module.name.rsplit(".", 1)[-1].endswith("events"):
            importlib.import_module(module.name)


def _subclasses(cls):
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _subclasses(subclass)


def _declared_auditable():
    _import_declared_events()
    return {cls.event_id: cls for cls in _subclasses(AuditableEvent) if cls.__dict__.get("mark") == "auditable"}


def _declared_loggable():
    _import_declared_events()
    return loggable_events()


def _documented(title: str) -> dict[str, str]:
    sections = {match["title"]: match["body"] for match in SECTION.finditer(PAGE.read_text())}
    return {match["id"]: match["body"] for match in ENTRY.finditer(sections[title])}


CATALOGUES = [
    pytest.param("Audit events", _declared_auditable, id="audit"),
    pytest.param("Loggable events", _declared_loggable, id="loggable"),
]


@pytest.mark.parametrize("title, declared", CATALOGUES)
def test_catalogue_lists_exactly_the_declared_events(title, declared):
    assert set(_documented(title)) == set(declared())


@pytest.mark.parametrize("title, declared", CATALOGUES)
def test_catalogue_names_the_details_of_each_event(title, declared):
    documented = _documented(title)
    for event_id, event_type in declared().items():
        missing = [name for name in event_type.details_fields if f"``{name}``" not in documented[event_id]]
        assert not missing, f"{event_id} does not document its details: {', '.join(missing)}"


def test_something_is_declared():
    assert _declared_auditable() and _declared_loggable()

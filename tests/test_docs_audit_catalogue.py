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
from harp.unit_of_work import auditable_events, loggable_events

PAGE = Path(__file__).parent.parent / "docs" / "operate" / "audit.rst"
SECTION = re.compile(r"^(?P<title>[^\n]+)\n:{3,}\n(?P<body>.*?)(?=^[^\n]+\n:{3,}\n|\Z)", re.MULTILINE | re.DOTALL)
ENTRY = re.compile(r"^``(?P<id>[\w.]+)``\n(?P<body>(?:(?: {4}.*)?\n)+)", re.MULTILINE)


def _import_declared_events():
    # An event declared outside these ``harp_apps/*events*`` modules is not discovered, so not checked.
    """Events are declared in the ``events`` modules of the applications; importing them registers the classes."""
    for module in pkgutil.walk_packages(harp_apps.__path__, "harp_apps."):
        if module.name.rsplit(".", 1)[-1].endswith("events"):
            importlib.import_module(module.name)


def _shipped(events):
    """The events the applications declare, not the ones other tests declare in the same process."""
    return {event_id: cls for event_id, cls in events.items() if cls.__module__.startswith("harp_apps.")}


def _declared_auditable():
    _import_declared_events()
    return _shipped(auditable_events())


def _declared_loggable():
    _import_declared_events()
    return _shipped(loggable_events())


def _documented(title: str) -> dict[str, str]:
    sections = {match["title"]: match["body"] for match in SECTION.finditer(PAGE.read_text())}
    return {match["id"]: match["body"] for match in ENTRY.finditer(sections[title])}


def _documented_details(body: str) -> set[str]:
    """The names on the entry's ``Details:`` line."""
    line = re.search(r"^ {4}Details: (.*)$", body, re.MULTILINE)
    return set(re.findall(r"``(\w+)``", line.group(1))) if line else set()


CATALOGUES = [
    pytest.param("Audit events", _declared_auditable, id="audit"),
    pytest.param("Loggable events", _declared_loggable, id="loggable"),
]


@pytest.mark.parametrize("title, declared", CATALOGUES)
def test_catalogue_lists_exactly_the_declared_events(title, declared):
    assert set(_documented(title)) == set(declared())


@pytest.mark.parametrize("title, declared", CATALOGUES)
def test_catalogue_names_exactly_the_details_of_each_event(title, declared):
    documented = _documented(title)
    for event_id, event_type in declared().items():
        assert _documented_details(documented[event_id]) == set(event_type.details_fields), event_id


def test_something_is_declared():
    assert _declared_auditable() and _declared_loggable()

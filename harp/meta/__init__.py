"""
The Meta (:mod:`harp.meta`) package provides tools to add metadata to objects.

Metadata are key-value pairs that can be attached to any object.

This package have no idea of what the metadata is used for, and it is up to the user to define its own usage.

"""

__title__ = "Meta"


def get_meta(subject, name, *, default=None):
    try:
        return subject.__metadata__.get(name, default)
    except AttributeError:
        return default


def set_meta(subject, name, value):
    try:
        metadata = subject.__metadata__
    except AttributeError:
        metadata = subject.__metadata__ = {}
    metadata[name] = value


def has_meta(subject, name):
    try:
        _ = subject.__metadata__
    except AttributeError:
        return False
    return name in subject.__metadata__

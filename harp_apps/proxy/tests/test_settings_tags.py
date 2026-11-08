"""Client tags are bounded by proxy settings."""

import pytest
from pydantic import ValidationError

from harp_apps.proxy.settings import ProxySettings
from harp_apps.storage.models.tags import Tag, TagValue


def test_tag_bounds_default():
    tags = ProxySettings().tags
    assert (tags.max_count, tags.max_name_length, tags.max_value_length) == (20, 64, 255)


def test_tag_bounds_are_settings():
    tags = ProxySettings(tags={"max_count": 5, "max_name_length": 8, "max_value_length": 16}).tags
    assert (tags.max_count, tags.max_name_length, tags.max_value_length) == (5, 8, 16)


def test_tag_bounds_cannot_exceed_storage_columns():
    assert ProxySettings(tags={"max_name_length": Tag.name.type.length}).tags.max_name_length == 64
    assert ProxySettings(tags={"max_value_length": TagValue.value.type.length}).tags.max_value_length == 255
    with pytest.raises(ValidationError):
        ProxySettings(tags={"max_name_length": Tag.name.type.length + 1})
    with pytest.raises(ValidationError):
        ProxySettings(tags={"max_value_length": TagValue.value.type.length + 1})

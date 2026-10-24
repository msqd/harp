"""Client tags are bounded by proxy settings."""

from harp_apps.proxy.settings import ProxySettings


def test_tag_bounds_default():
    tags = ProxySettings().tags
    assert (tags.max_count, tags.max_name_length, tags.max_value_length) == (20, 64, 256)


def test_tag_bounds_are_settings():
    tags = ProxySettings(tags={"max_count": 5, "max_name_length": 8, "max_value_length": 16}).tags
    assert (tags.max_count, tags.max_name_length, tags.max_value_length) == (5, 8, 16)

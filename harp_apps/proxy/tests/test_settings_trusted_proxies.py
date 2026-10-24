from ipaddress import ip_network

import pytest
from pydantic import ValidationError

from harp_apps.proxy.settings import ProxySettings


def test_trusted_proxies_are_empty_by_default():
    assert ProxySettings().trusted_proxies == []


def test_trusted_proxies_are_cidr_ranges():
    settings = ProxySettings(trusted_proxies=["10.0.0.0/8", "fd00::/8", "192.168.1.1"])

    assert settings.trusted_proxies == [ip_network("10.0.0.0/8"), ip_network("fd00::/8"), ip_network("192.168.1.1/32")]


def test_trusted_proxies_refuse_garbage():
    with pytest.raises(ValidationError):
        ProxySettings(trusted_proxies=["not-a-network"])

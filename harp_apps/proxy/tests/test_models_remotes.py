import pytest

from harp_apps.proxy.models.remotes import Remote


def test_remote_round_robin():
    remote = Remote("api", base_urls=("http://api0.example.com/", "http://api1.example.com/"))

    assert remote.name == "api"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"

    remote.set_down("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api0.example.com/"

    remote.set_up("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"


def test_remote_fallback():
    remote = Remote(
        "api",
        base_urls=("http://api0.example.com/", "http://api1.example.com/"),
        fallback_urls=("http://fallback.example.com",),
        min_pool_size=2,
    )

    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"

    remote.set_down("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://fallback.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://fallback.example.com/"

    remote.set_up("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"


def test_empty_pool():
    remote = Remote("test")
    with pytest.raises(IndexError):
        remote.get_url()


def test_empty_pool_after_down():
    remote = Remote("test", base_urls=["http://example.com"])
    assert remote.get_url() == "http://example.com/"
    remote.set_down("http://example.com")
    with pytest.raises(IndexError):
        remote.get_url()
    remote.set_up("http://example.com")
    assert remote.get_url() == "http://example.com/"

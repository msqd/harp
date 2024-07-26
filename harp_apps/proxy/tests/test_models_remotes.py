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
    assert remote.get_url() == "http://fallback.example.com"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://fallback.example.com"

    remote.set_up("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"

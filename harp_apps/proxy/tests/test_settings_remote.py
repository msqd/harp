from harp.config import asdict
from harp_apps.proxy.settings.remote import RemoteSettings


def test_defaults():
    settings = RemoteSettings()
    assert asdict(settings) == {}

    assert asdict(settings, verbose=True) == {
        "break_on": ["network_error", "unhandled_exception"],
        "check_after": 10.0,
        "endpoints": None,
        "min_pool_size": 1,
        "probe": None,
    }

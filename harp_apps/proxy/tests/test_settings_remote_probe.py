from harp.config import asdict
from harp_apps.proxy.settings.remote import RemoteProbeSettings


def test_defaults():
    settings = RemoteProbeSettings()

    assert asdict(settings) == {}

    assert asdict(settings, verbose=True) == {
        "method": "GET",
        "path": "/",
        "headers": {},
        "interval": 10.0,
        "timeout": 10.0,
        "verify": True,
    }

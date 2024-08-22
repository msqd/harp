from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.settings.remote.probe import RemoteProbe, RemoteProbeSettings


class TestRemoteProbeSettings(BaseConfigurableTest):
    type = RemoteProbeSettings
    initial = {}
    expected = {}
    expected_verbose = {
        "headers": {},
        "interval": 10.0,
        "method": "GET",
        "path": "/",
        "timeout": 10.0,
        "verify": True,
    }


class TestRemoteProbeStateful(BaseConfigurableTest):
    type = RemoteProbe
    initial = {"settings": TestRemoteProbeSettings.initial}
    expected = {"settings": TestRemoteProbeSettings.expected_verbose}
    expected_verbose = {"settings": TestRemoteProbeSettings.expected_verbose}

from harp_apps.proxy.settings.remote.probe import RemoteProbe, RemoteProbeSettings
from harp_apps.proxy.tests._base import BaseModelTest


class TestRemoteProbeSettings(BaseModelTest):
    type = RemoteProbeSettings
    initial = {}
    expected = {}
    expected_verbose = {
        "headers": {},
        "interval": "10.0",
        "method": "GET",
        "path": "/",
        "timeout": "10.0",
        "verify": True,
    }


class TestRemoteProbeModel(BaseModelTest):
    type = RemoteProbe
    initial = {"settings": TestRemoteProbeSettings.initial}
    expected = {"settings": TestRemoteProbeSettings.expected_verbose}
    expected_verbose = {"settings": TestRemoteProbeSettings.expected_verbose}

import builtins
import hashlib
from unittest.mock import patch

import pytest

builtins.__pytest__ = True

DISABLED_APPLICATIONS_FOR_TESTS = ("telemetry", "harp_apps.telemetry")

DEFAULT_STORAGE_SETTINGS = {
    "url": "sqlite+aiosqlite:///:memory:",
    "migrate": False,
}


@pytest.fixture
def test_id(request):
    return hashlib.md5(str(request.node.nodeid).encode("utf-8")).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def default_session_fixture():
    from harp.config import Config

    DEFAULT_APPLICATIONS_FOR_TESTS = list(Config.DEFAULT_APPLICATIONS)
    for app in DISABLED_APPLICATIONS_FOR_TESTS:
        if app in DEFAULT_APPLICATIONS_FOR_TESTS:
            DEFAULT_APPLICATIONS_FOR_TESTS.remove(app)

    with patch("harp.config.Config.DEFAULT_APPLICATIONS", DEFAULT_APPLICATIONS_FOR_TESTS):
        yield


# see https://github.com/GrahamDumpleton/wrapt/issues/257
@pytest.fixture(autouse=True, scope="session")
def patch_wrapt_for_pycharm():
    from wrapt import FunctionWrapper, decorators
    from wrapt.decorators import AdapterWrapper, _AdapterFunctionSurrogate

    class _PatchedAdapterFunctionSurrogate(_AdapterFunctionSurrogate):
        @property
        def __class__(self):
            try:
                return super().__class__
            except ValueError:
                return type(self)

    class PatchedAdapterWrapper(AdapterWrapper):
        def __init__(self, *args, **kwargs):
            adapter = kwargs.pop("adapter")
            FunctionWrapper.__init__(self, *args, **kwargs)
            self._self_surrogate = _PatchedAdapterFunctionSurrogate(self.__wrapped__, adapter)
            self._self_adapter = adapter

        @property
        def __class__(self):
            try:
                return super().__class__
            except ValueError:
                return type(self)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(decorators, "AdapterWrapper", PatchedAdapterWrapper)
        yield


@pytest.fixture(scope="session")
def httpbin():
    from testcontainers.core.container import DockerContainer

    from harp.utils.network import wait_for_port

    with DockerContainer("mccutchen/go-httpbin:v2.13.2").with_exposed_ports(8080) as container:
        wait_for_port(int(container.get_exposed_port(8080)), container.get_container_host_ip())
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"

import harp.controllers
import harp.controllers.default


def test_dump_request_controller_is_not_exposed():
    assert not hasattr(harp.controllers, "dump_request_controller")
    assert not hasattr(harp.controllers.default, "dump_request_controller")
    assert "dump_request_controller" not in harp.controllers.__all__

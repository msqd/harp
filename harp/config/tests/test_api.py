def _no_private(x):
    return not x.startswith("_")


def test_exposed_api(snapshot):
    """This test snapshots the public API of the harp.config module, to make sure that api changes are conscious
    choices and not coincidences."""
    api = __import__("harp.config", fromlist=["*"])
    assert list(filter(_no_private, dir(api))) == snapshot

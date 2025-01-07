def test_exposed_api(snapshot):
    """This test snapshots the public API of the harp.config module, to make sure that api changes are conscious
    choices and not coincidences."""
    api = __import__("harp.config", fromlist=["*"])

    api_elements = []
    for element in dir(api):
        if element not in api.__all__:
            continue

        api_elements.append(element)

    assert api_elements == snapshot

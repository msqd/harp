from harp.http import HttpRequest
from harp_apps.proxy.helpers import extract_tags_from_request
from harp_apps.proxy.settings import TagsSettings


def _request(headers):
    return HttpRequest(headers=headers)


def test_tags_are_extracted_and_consumed():
    request = _request({"X-Harp-Foo": "bar", "accept": "text/plain"})

    tags, dropped = extract_tags_from_request(request, TagsSettings())

    assert tags == {"foo": "bar"}
    assert dropped == []
    assert "x-harp-foo" not in request.headers
    assert request.headers["accept"] == "text/plain"


def test_tags_over_the_count_are_dropped_keeping_the_first_in_header_order():
    request = _request({f"x-harp-t{i}": "v" for i in range(200)})

    tags, dropped = extract_tags_from_request(request, TagsSettings())

    assert list(tags) == [f"t{i}" for i in range(20)]
    assert len(dropped) == 180
    assert not any(h.startswith("x-harp-") for h in request.headers)


def test_oversized_name_or_value_is_dropped_and_does_not_count():
    request = _request(
        {
            "x-harp-" + "n" * 65: "v",
            "x-harp-long": "v" * 256,
            "x-harp-a": "1",
            "x-harp-b": "2",
        }
    )

    tags, dropped = extract_tags_from_request(request, TagsSettings(max_count=2))

    assert tags == {"a": "1", "b": "2"}
    assert len(dropped) == 2


def test_bounds_are_inclusive():
    request = _request({"x-harp-" + "n" * 64: "v" * 255})

    tags, dropped = extract_tags_from_request(request, TagsSettings())

    assert tags == {"n" * 64: "v" * 255}
    assert dropped == []


def test_dropped_report_names_the_tag_not_the_value():
    request = _request({"x-harp-secret": "v" * 256})

    _, dropped = extract_tags_from_request(request, TagsSettings())

    assert dropped == [("secret", "value too long")]

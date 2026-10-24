from harp.http import HttpRequest
from harp_apps.proxy.constants import CHECKING, DOWN, UP
from harp_apps.proxy.settings import TagsSettings


def humanize_status(status):
    return {CHECKING: "checking", UP: "up", DOWN: "down"}.get(status, "unknown")


def extract_tags_from_request(
    request: HttpRequest, limits: TagsSettings
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """
    Convert special request headers (x-harp-*) into tags (key-value pairs) that we'll attach to the
    transaction. Headers are "consumed", meaning they are removed from the request headers.

    Tags are bounded by ``limits``: oversized ones are dropped first and do not count, then only the first
    ``max_count`` in header order are kept.

    :return: the kept tags, and the dropped ones as (name, reason) pairs.
    """

    tags: dict[str, str] = {}
    dropped: list[tuple[str, str]] = []
    headers_to_remove = []

    for header in request.headers:
        lower_header = header.lower()
        if not lower_header.startswith("x-harp-"):
            continue
        headers_to_remove.append(header)
        name, value = lower_header[7:], request.headers[header]
        if len(name) > limits.max_name_length:
            dropped.append((name[: limits.max_name_length], "name too long"))
        elif len(value) > limits.max_value_length:
            dropped.append((name, "value too long"))
        elif len(tags) >= limits.max_count:
            dropped.append((name, "too many tags"))
        else:
            tags[name] = value

    for header in headers_to_remove:
        request.headers.pop(header)

    return tags, dropped

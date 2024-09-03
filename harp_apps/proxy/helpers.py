from harp.http import HttpRequest
from harp_apps.proxy.constants import CHECKING, DOWN, UP


def humanize_status(status):
    return {CHECKING: "checking", UP: "up", DOWN: "down"}.get(status, "unknown")


def extract_tags_from_request(request: HttpRequest):
    """
    Convert special request headers (x-harp-*) into tags (key-value pairs) that we'll attach to the
    transaction. Headers are "consumed", meaning they are removed from the request headers.
    """

    tags = {}
    headers_to_remove = []

    for header in request.headers:
        lower_header = header.lower()
        if lower_header.startswith("x-harp-"):
            tags[lower_header[7:]] = request.headers[header]
            headers_to_remove.append(header)

    for header in headers_to_remove:
        request.headers.pop(header)

    return tags

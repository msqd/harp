from harp_apps.proxy.constants import CHECKING, DOWN, UP


def humanize_status(status):
    return {CHECKING: "checking", UP: "up", DOWN: "down"}.get(status, "unknown")

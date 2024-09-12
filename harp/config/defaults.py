import importlib.util
import os

DEFAULT_SYSTEM_CONFIG_FILENAMES = (
    "/etc/harp.yaml",
    "/etc/harp.yml",
)

DEFAULT_APPLICATIONS = (
    "http_client",
    "proxy",
    "storage",
    "dashboard",
    "harp_apps.contrib.sentry",
    "telemetry",
    "janitor",
)

_NAMESPACES = os.getenv("NAMESPACES", None)
_DEFAULT_NAMESPACE_CANDIDATES = (*(_NAMESPACES.split(",") if _NAMESPACES else ()), "harp_apps")
DEFAULT_NAMESPACES = []
for _namespace in _DEFAULT_NAMESPACE_CANDIDATES:
    try:
        if importlib.util.find_spec(_namespace):
            DEFAULT_NAMESPACES.append(_namespace)
    except ModuleNotFoundError:
        pass
DEFAULT_NAMESPACES = tuple(DEFAULT_NAMESPACES)

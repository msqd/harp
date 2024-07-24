import importlib.util

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

_DEFAULT_NAMESPACE_CANDIDATES = (
    "harp_enterprise",
    "harp_pro",
    "harp_apps",
)
DEFAULT_NAMESPACES = []
for _namespace in _DEFAULT_NAMESPACE_CANDIDATES:
    try:
        if importlib.util.find_spec(_namespace):
            DEFAULT_NAMESPACES.append(_namespace)
    except ModuleNotFoundError:
        pass
DEFAULT_NAMESPACES = tuple(DEFAULT_NAMESPACES)

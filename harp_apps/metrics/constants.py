from prometheus_client import Counter, Gauge, Histogram

CONTROLLER_REQUESTS = Counter(
    "controller_requests_count",
    "Count of controller requests by route name, port and method.",
    ["name", "port", "method"],
)
CONTROLLER_REQUESTS_TIME = Histogram(
    "controller_requests_time",
    "Histogram of controller requests processing time by route name, port and method (in seconds)",
    ["name", "port", "method"],
)
CONTROLLER_REQUESTS_IN_PROGRESS = Gauge(
    "controller_requests_in_progress",
    "Gauge of controller requests by route name, port and method currently being processed",
    ["name", "port", "method"],
)
CONTROLLER_RESPONSES = Counter(
    "controller_responses_count",
    "Count of controller responses by route name, port, method and status and status codes.",
    ["name", "port", "method", "status"],
)
CONTROLLER_EXCEPTIONS = Counter(
    "controller_exceptions_count",
    "Count of exceptions raised in controllers by route name, port, method, path and exception type",
    ["name", "port", "method", "path", "exception"],
)
REMOTE_REQUESTS = Counter(
    "remote_requests_count",
    "Count of remote requests by route name and method.",
    ["name", "method"],
)
REMOTE_REQUESTS_TIME = Histogram(
    "remote_requests_time",
    "Histogram of remote requests processing time by route name and method (in seconds)",
    ["name", "method"],
)
REMOTE_REQUESTS_IN_PROGRESS = Gauge(
    "remote_requests_in_progress",
    "Gauge of remote requests by route name and method currently being processed",
    ["name", "method"],
)
REMOTE_RESPONSES = Counter(
    "remote_responses_count",
    "Count of remote responses by route name, method and status and status codes.",
    ["name", "method", "status"],
)
REMOTE_EXCEPTIONS = Counter(
    "remote_exceptions_count",
    "Count of exceptions raised in remotes by route name, method, path and exception type",
    ["name", "method", "url", "exception"],
)

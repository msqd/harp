from enum import Enum


class TimeBucket(Enum):
    YEAR = "year"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"


# Transaction markers that control storage behavior
SKIP_STORAGE = "skip-storage"
SKIP_REQUEST_STORAGE = "skip-request-storage"
SKIP_RESPONSE_STORAGE = "skip-response-storage"
SKIP_REQUEST_BODY_STORAGE = "skip-request-body-storage"
SKIP_RESPONSE_BODY_STORAGE = "skip-response-body-storage"
SKIP_REQUEST_HEADERS_STORAGE = "skip-request-headers-storage"
SKIP_RESPONSE_HEADERS_STORAGE = "skip-response-headers-storage"

# Transaction markers set by the storage worker when it sheds data under pressure
SHED_MESSAGES = "shed-messages"
SHED_HEADERS = "shed-headers"
SHED_BODIES = "shed-bodies"

# Transaction markers set when a recording cap cuts data (#911)
TRUNCATED_REQUEST_BODY = "truncated-request-body"
TRUNCATED_RESPONSE_BODY = "truncated-response-body"

# How much of a request or response body HARP records, and holds in memory per body, at most (#911)
DEFAULT_MAX_RECORDED_BODY_SIZE = 1024 * 1024

# Transaction marker set when the client went away before the end of the response body (#911)
CLIENT_DISCONNECTED = "client-disconnected"

# Transaction marker set when the proxy removed HARP's own credentials from the request before the origin (ADR-0010)
HARP_CREDENTIALS_STRIPPED = "harp-credentials-stripped"

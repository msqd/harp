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
TRUNCATED_RESPONSE_BODY = "truncated-response-body"

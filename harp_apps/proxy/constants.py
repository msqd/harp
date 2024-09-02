from ssl import SSLCertVerificationError

import httpcore
import httpx

BREAK_ON_HTTP_4xx = "http_4xx"
BREAK_ON_HTTP_5xx = "http_5xx"
BREAK_ON_NETWORK_ERROR = "network_error"
BREAK_ON_UNHANDLED_EXCEPTION = "unhandled_exception"

DOWN = -1
CHECKING = 0
UP = 1

DEFAULT_POOL = "default"
FALLBACK_POOL = "fallback"
AVAILABLE_POOLS = {DEFAULT_POOL, FALLBACK_POOL}

ALL_BREAK_ON_VALUES = {
    BREAK_ON_HTTP_4xx,
    BREAK_ON_HTTP_5xx,
    BREAK_ON_NETWORK_ERROR,
    BREAK_ON_UNHANDLED_EXCEPTION,
}

ERR_UNHANDLED_STATUS_CODE = 500
ERR_UNHANDLED_MESSAGE = "Unhandled error"
ERR_UNHANDLED_VERBOSE_MESSAGE = "Internal Server Error (unhandled error)"

ERR_UNAVAILABLE_STATUS_CODE = 503
ERR_UNAVAILABLE_MESSAGE = "Unavailable"
ERR_UNAVAILABLE_VERBOSE = "Service Unavailable (remote server unavailable)"

ERR_TIMEOUT_STATUS_CODE = 504
ERR_TIMEOUT_MESSAGE = "Timeout"
ERR_TIMEOUT_VERBOSE_MESSAGE = "Gateway Timeout (remote server timeout)"

ERR_REMOTE_STATUS_CODE = 502
ERR_REMOTE_MESSAGE = "Remote server disconnected"
ERR_REMOTE_VERBOSE_MESSAGE = "Bad Gateway (remote server disconnected)"

ERR_SSL_STATUS_CODE = 526
ERR_SSL_MESSAGE = "Invalid SSL certificate"
ERR_SSL_VERBOSE_MESSAGE = "Invalid SSL Certificate (certificate verification failed)"

NETWORK_ERRORS = {
    httpcore.NetworkError: (
        ERR_UNAVAILABLE_STATUS_CODE,
        ERR_UNAVAILABLE_MESSAGE,
        ERR_UNAVAILABLE_VERBOSE,
    ),
    httpx.NetworkError: (
        ERR_UNAVAILABLE_STATUS_CODE,
        ERR_UNAVAILABLE_MESSAGE,
        ERR_UNAVAILABLE_VERBOSE,
    ),
    httpcore.TimeoutException: (
        ERR_TIMEOUT_STATUS_CODE,
        ERR_TIMEOUT_MESSAGE,
        ERR_TIMEOUT_VERBOSE_MESSAGE,
    ),
    httpx.TimeoutException: (
        ERR_TIMEOUT_STATUS_CODE,
        ERR_TIMEOUT_MESSAGE,
        ERR_TIMEOUT_VERBOSE_MESSAGE,
    ),
    httpcore.RemoteProtocolError: (
        ERR_REMOTE_STATUS_CODE,
        ERR_REMOTE_MESSAGE,
        ERR_REMOTE_VERBOSE_MESSAGE,
    ),
    httpx.RemoteProtocolError: (
        ERR_REMOTE_STATUS_CODE,
        ERR_REMOTE_MESSAGE,
        ERR_REMOTE_VERBOSE_MESSAGE,
    ),
    SSLCertVerificationError: (
        ERR_SSL_STATUS_CODE,
        ERR_SSL_MESSAGE,
        ERR_SSL_VERBOSE_MESSAGE,
    ),
}

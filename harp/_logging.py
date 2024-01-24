import logging.config
import os

import structlog

processors = [
    structlog.stdlib.filter_by_level,
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.dev.set_exc_info,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.UnicodeDecoder(),
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]

structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    processors=processors,
    cache_logger_on_first_use=True,
)

LOGGING_FORMATTERS = {
    "json": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.JSONRenderer(),
    },
    "plain": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback, colors=False),
    },
    "pretty": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback),
    },
    "keyvalue": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event", "logger"]),
    },
}

LOGGING_DEFAULT_FORMATTER = "pretty"
LOGGING_FORMATTER = os.environ.get("LOGGING_FORMATTER", LOGGING_DEFAULT_FORMATTER)
if LOGGING_FORMATTER not in LOGGING_FORMATTERS:
    LOGGING_FORMATTER = LOGGING_DEFAULT_FORMATTER

logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": LOGGING_FORMATTERS,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOGGING_FORMATTER,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": logging.INFO,
    },
    "loggers": {
        "harp": {"level": os.environ.get("LOGGING_HARP", "INFO")},
        "harp.core.event_dispatcher": {"level": os.environ.get("LOGGING_HARP_EVENTS", "WARNING")},
        "httpcore": {"level": os.environ.get("LOGGING_HTTPCORE", "INFO")},  # todo wrap in structlog
        "httpx": {"level": os.environ.get("LOGGING_HTTPX", "WARNING")},  # todo wrap in structlog
        "hypercorn.access": {"level": os.environ.get("LOGGING_HYPERCORN_ACCESS", "WARNING")},
        "hypercorn.error": {"level": os.environ.get("LOGGING_HYPERCORN_ERROR", "INFO")},
    },
}

logging.config.dictConfig(logging_config)

get_logger = structlog.get_logger

__all__ = ["get_logger"]

import logging
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
        "processor": structlog.dev.ConsoleRenderer(colors=False),
    },
    "pretty": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(),
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
        "harp": {"level": "DEBUG"},
        "httpx": {"level": "DEBUG"},
        "httpcore": {"level": "DEBUG"},
    },
}

logging.config.dictConfig(logging_config)

getLogger = structlog.getLogger


__all__ = ["getLogger"]

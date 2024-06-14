import logging.config
import os
from typing import Any

import structlog

shared_processors = [
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.ExtraAdder(),
    structlog.processors.TimeStamper(fmt="iso"),
]

processors = [
    structlog.stdlib.filter_by_level,
    structlog.contextvars.merge_contextvars,
    *shared_processors,
    structlog.dev.set_exc_info,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.UnicodeDecoder(),
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]

try:
    _exc_formatter_options = {"width": os.get_terminal_size()[0]}
except OSError:
    _exc_formatter_options = {}


LOGGING_FORMATTERS = {
    "json": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.JSONRenderer(),
        "foreign_pre_chain": shared_processors,
    },
    "plain": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback, colors=False),
        "foreign_pre_chain": shared_processors,
    },
    "pretty": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.RichTracebackFormatter(**_exc_formatter_options)
        ),
        "foreign_pre_chain": shared_processors,
    },
    "keyvalue": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event", "logger"]),
        "foreign_pre_chain": shared_processors,
    },
}

DEFAULT_LOGGING_FORMAT = "pretty"
LOGGING_FORMAT = os.environ.get("LOGGING_FORMAT", DEFAULT_LOGGING_FORMAT)
if LOGGING_FORMAT not in LOGGING_FORMATTERS:
    LOGGING_FORMAT = DEFAULT_LOGGING_FORMAT

logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": LOGGING_FORMATTERS,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOGGING_FORMAT,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": logging.INFO,
    },
    "loggers": {
        "harp": {"level": os.environ.get("LOGGING_HARP", "INFO")},
        "harp_apps": {"level": os.environ.get("LOGGING_HARP", "INFO")},
        "harp.event_dispatcher": {"level": os.environ.get("LOGGING_HARP_EVENTS", "WARNING")},
        "httpcore": {"level": os.environ.get("LOGGING_HTTP", "WARNING")},  # todo wrap in structlog
        "httpx": {"level": os.environ.get("LOGGING_HTTP", "WARNING")},  # todo wrap in structlog
        "hypercorn.access": {"level": os.environ.get("LOGGING_HYPERCORN_ACCESS", "WARNING")},
        "hypercorn.error": {"level": os.environ.get("LOGGING_HYPERCORN_ERROR", "INFO")},
        "sqlalchemy.engine": {"level": os.environ.get("LOGGING_SQLALCHEMY", "WARNING")},
    },
}


logging.config.dictConfig(logging_config)

structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    processors=processors,
    cache_logger_on_first_use=True,
)


def get_logger(name, *args: Any, **initial_values: Any) -> Any:
    if name == "env_py":
        name = "__migrations__"
    else:
        pkg, mod = name.rsplit(".", 1)
        if mod in ("__init__", "__main__", "__app__"):
            name = pkg

    return structlog.get_logger(name, *args, **initial_values)


__all__ = ["get_logger"]

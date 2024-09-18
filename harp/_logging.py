import logging.config
import os
from typing import Any, Optional

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
        "processor": structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.plain_traceback,
            colors=False,
        ),
        "foreign_pre_chain": shared_processors,
    },
    "pretty": {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.plain_traceback,
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


def _get_logging_level(name: Optional[str], *, default="warning"):
    varname = "_".join(filter(None, ("LOGGING", name.upper() if name is not None else None)))
    return os.environ.get(varname, default).upper()


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
        "level": _get_logging_level(None, default="info"),
    },
    "loggers": {
        "harp": {"level": _get_logging_level("harp", default="info")},
        "harp.event_dispatcher": {"level": _get_logging_level("events")},
        "harp_apps": {"level": _get_logging_level("harp")},
        "harp_apps.http_client": {"level": _get_logging_level("http_client")},
        "harp_apps.proxy": {"level": _get_logging_level("proxy")},
        "httpcore": {"level": _get_logging_level("http_core")},
        "httpx": {"level": _get_logging_level("http_core")},
        "hypercorn.access": {"level": _get_logging_level("http", default="info")},
        "hypercorn.error": {"level": _get_logging_level("http", default="info")},
        "sqlalchemy.engine": {"level": _get_logging_level("sql")},
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
        try:
            pkg, mod = name.rsplit(".", 1)
        except ValueError:
            return structlog.get_logger(name, *args, **initial_values)
        if mod in ("__init__", "__main__", "__app__"):
            name = pkg

    return structlog.get_logger(name, *args, **initial_values)


__all__ = ["get_logger"]

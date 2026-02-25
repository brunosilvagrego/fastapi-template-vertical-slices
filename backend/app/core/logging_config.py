from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        # app logs
        "app": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # uvicorn logs
        "uvicorn": {"handlers": ["console"], "level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"level": "INFO"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


def setup_logging():
    dictConfig(LOGGING_CONFIG)

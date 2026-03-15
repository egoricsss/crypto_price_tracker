import logging
import logging.config
import sys
from typing import Optional

from app.core.config import settings


class LogConfig:
    def __init__(
        self,
        log_level: str = "INFO",
        log_format: Optional[str] = None,
        date_format: str = "%Y-%m-%d %H:%M:%S",
    ) -> None:
        self.log_level = log_level.upper()
        self.date_format = date_format
        # Структурированный формат логов для удобства чтения и парсинга
        self.log_format = log_format or (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        )

    def configure(self) -> None:
        """
        Настраивает корневой логгер и базовые обработчики.
        """
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.log_format,
                    "datefmt": self.date_format,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                    "level": self.log_level,
                },
            },
            "root": {
                "level": self.log_level,
                "handlers": ["console"],
            },
            "loggers": {
                "app": {
                    "level": self.log_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "celery": {
                    "level": self.log_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        logging.config.dictConfig(log_config)


def setup_logging() -> None:
    config = LogConfig(
        log_level=settings.app.log_level,
    )
    config.configure()


def get_logger(name: str) -> logging.Logger:
    # Приводим имя к виду 'app.module_name' для иерархии
    logger_name = f"app.{name}" if not name.startswith("app.") else name
    return logging.getLogger(logger_name)

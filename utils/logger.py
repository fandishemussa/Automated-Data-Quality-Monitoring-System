"""Centralized logging configuration for the project."""

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "app.log"
APP_LOGGER_NAME = "automated_data_quality_monitoring"


def configure_logging(level=logging.INFO):
    """Configure application logging once for console and file output.

    Console logs stay concise at INFO level by default. The file log keeps DEBUG
    messages too, which is useful for database and troubleshooting details.
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(logging.DEBUG)
    app_logger.propagate = False

    if getattr(app_logger, "_adqms_logging_configured", False):
        return app_logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)
    app_logger._adqms_logging_configured = True

    return app_logger


def get_logger(module_name=None):
    """Return a module-specific logger using the shared configuration."""

    configure_logging()

    if module_name:
        return logging.getLogger(f"{APP_LOGGER_NAME}.{module_name}")

    return logging.getLogger(APP_LOGGER_NAME)
